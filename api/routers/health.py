from fastapi import APIRouter
from pydantic import BaseModel
import os
import logging
import time

logger = logging.getLogger(__name__)

# Note: The main app likely includes this router without a prefix or with /health.
# I will keep the existing path '/health' to avoid breaking existing integrations.
router = APIRouter()

class HealthResponse(BaseModel):
    status: str
    redis: str
    celery: str
    timestamp: float

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Exposes service health status for deployment monitoring.
    Checks Redis connectivity and tries to ping Celery workers.
    """
    redis_status = "unknown"
    celery_status = "unknown"
    
    import asyncio
    
    # Check Redis
    try:
        from services.infrastructure.redis_pool import get_redis_client
        
        def _ping_redis():
            client = get_redis_client()
            return client and client.ping()
            
        is_redis_up = await asyncio.to_thread(_ping_redis)
        if is_redis_up:
            redis_status = "connected"
        else:
            redis_status = "disconnected"
    except Exception as e:
        logger.error(f"Health check: Redis ping failed - {e}")
        redis_status = "error"
        
    # Check Celery
    try:
        from worker import celery_app
        # Ping workers with a short timeout to prevent blocking
        # i.celery returns a dict of worker responses. Empty means no workers listening.
        def _ping_celery():
            i = celery_app.control.inspect(timeout=1.0)
            return i.ping() if i else None
            
        workers = await asyncio.to_thread(_ping_celery)
        if workers:
            celery_status = "connected"
        else:
            celery_status = "no_workers_found"
    except Exception as e:
        logger.error(f"Health check: Celery ping failed - {e}")
        celery_status = "error"
        
    overall_status = "healthy" if redis_status == "connected" and celery_status == "connected" else "degraded"
        
    response_body = HealthResponse(
        status=overall_status,
        redis=redis_status,
        celery=celery_status,
        timestamp=time.time()
    )
    
    if overall_status != "healthy":
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail=response_body.dict())
        
    return response_body