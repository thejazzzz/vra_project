# File: services/llm/token_manager.py
import logging
from typing import Optional

try:
    import tiktoken
except ImportError:
    tiktoken = None

logger = logging.getLogger(__name__)

class TokenManager:
    """
    Responsibilities:
    - track token usage
    - enforce limits
    - truncate context safely
    """
    def __init__(self, default_limit: int = 4000):
        self.default_limit = default_limit
        self.encoding = None
        if tiktoken:
            try:
                self.encoding = tiktoken.get_encoding("cl100k_base")
            except Exception as e:
                logger.warning(f"Could not load tiktoken encoding: {e}")

    def count_tokens(self, text: str) -> int:
        if not text:
            return 0
        if self.encoding:
            return len(self.encoding.encode(text))
        # Rough fallback estimation: 1 token ~= 4 characters in English
        return len(text) // 4

    def truncate_to_limit(self, text: str, max_tokens: Optional[int] = None) -> str:
        limit = max_tokens if max_tokens is not None else self.default_limit
        if self.count_tokens(text) <= limit:
            return text
            
        if self.encoding:
            tokens = self.encoding.encode(text)
            return self.encoding.decode(tokens[:limit])
            
        # Fallback truncation
        chars = limit * 4
        return text[:chars] + "..."

    def add_and_check_budget(self, session_id: str, new_tokens: int, max_budget: int = 50000) -> bool:
        """
        Tracks total tokens used for a session globally via Redis.
        Returns True if within budget, False if exceeded.
        """
        try:
            from services.infrastructure.redis_pool import get_redis_client
            redis_client = get_redis_client()
            if not redis_client:
                return True
                
            key = f"token_budget:{session_id}"
            total = redis_client.incrby(key, new_tokens)
            
            # Ensure a TTL is always set if one is missing, protecting against unbounded memory leaks.
            # This handles cases where keys might have been created without TTLs by older code versions.
            if redis_client.ttl(key) == -1: # -1 means no expiry
                redis_client.expire(key, self.SESSION_TTL)
                
            if total > max_budget:
                from services.observability.metrics_logger import MetricsLogger
                MetricsLogger.log_token_usage_warning(session_id, total, max_budget)
                return False
                
        except Exception as e:
            logger.warning(f"TokenManager: Failed to track budget for {session_id}: {e}")
            
        return True
