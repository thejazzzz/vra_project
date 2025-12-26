import time
import asyncio
from fastapi import Request
from fastapi.responses import JSONResponse
import logging
from cachetools import TTLCache

logger = logging.getLogger("rate_limiter")

class RateLimitMiddleware:
    """
    Simple in-memory rate limiter using Fixed Window algorithm.
    Thread-safe and memory-bounded using asyncio locks and TTLCache.
    """
    def __init__(self, requests_per_minute: int = 60):
        self.rate_limit = requests_per_minute
        self.window_size = 60 # seconds
        self.clients = TTLCache(maxsize=10000, ttl=self.window_size) # IP -> list of timestamps
        self.global_lock = asyncio.Lock() 
        self.client_locks = {} # Plain dict 
        self.cleanup_task = None
        self._cleanup_lock = asyncio.Lock() # Guard for cleanup task creation
        
    async def _cleanup_loop(self):
        """Background task to prune unused locks."""
        while True:
            await asyncio.sleep(60) # Run every minute
            try:
                # 1. Snapshot keys under lock (fast)
                async with self.global_lock:
                    current_keys = list(self.client_locks.keys())
                
                # 2. Identify orphans (cpu bound, no lock)
                orphans = [ip for ip in current_keys if ip not in self.clients]
                
                # 3. Remove orphans under lock
                if orphans:
                    async with self.global_lock:
                        for ip in orphans:
                            # Double-check existence to avoid race with new request creating it
                            if ip not in self.clients and ip in self.client_locks:
                                del self.client_locks[ip]
            except Exception as e:
                logger.error(f"Rate limit cleanup failed: {e}")

    async def __call__(self, request: Request, call_next):
        # Lazy start background task with double-checked locking
        if self.cleanup_task is None:
            async with self._cleanup_lock:
                if self.cleanup_task is None:
                    self.cleanup_task = asyncio.create_task(self._cleanup_loop())

        # Skip rate limiting for static files or safe paths if needed
        if request.url.path == "/health" or request.method == "OPTIONS":
            return await call_next(request)

        # Robust Client IP Extraction (Strict)
        client_ip = None
        
        # 1. x-forwarded-for (standard proxy header)
        x_forwarded = request.headers.get("x-forwarded-for")
        if x_forwarded:
            client_ip = x_forwarded.split(",")[0].strip()
        # 2. x-real-ip (nginx/others)
        elif request.headers.get("x-real-ip"):
             client_ip = request.headers.get("x-real-ip").strip()
        # 3. Direct client host
        elif request.client and request.client.host:
            client_ip = request.client.host
            
        if not client_ip:
            # Reject unknown clients to prevent bucket sharing attacks
            logger.warning("Rate limit skipped due to missing client IP (blocking request)")
            return JSONResponse(
                status_code=400, 
                content={"detail": "Client IP required for rate limiting."}
            )
        
        # 1. Acquire global guard to safely get/create per-client lock
        async with self.global_lock:
            if client_ip not in self.client_locks:
                self.client_locks[client_ip] = asyncio.Lock()
                
                # PRE-REGISTER: Ensure client exists in cache so background cleaner 
                # doesn't delete the lock before we use it.
                if client_ip not in self.clients:
                     self.clients[client_ip] = []
                     
            client_lock = self.client_locks[client_ip]
        
        # 2. Acquire per-client lock to access/modify shared state
        async with client_lock:
            current_time = time.time()
            
            # Fetch history 
            history = self.clients.get(client_ip, [])
            
            # Cleanup old timestamps (sliding window)
            history = [t for t in history if t > current_time - self.window_size]
            
            # Check limit
            if len(history) >= self.rate_limit:
                self.clients[client_ip] = history
                logger.warning(f"Rate limit exceeded for IP: {client_ip}")
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Too many requests. Please try again later."}
                )
                
            # Add request
            history.append(current_time)
            self.clients[client_ip] = history # Updates entry and resets TTL (extends life)
        
        response = await call_next(request)
        return response
