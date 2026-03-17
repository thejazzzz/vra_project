import os
import redis
import logging

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Create a global connection pool
try:
    redis_pool = redis.ConnectionPool.from_url(REDIS_URL, decode_responses=True)
    redis_client = redis.Redis(connection_pool=redis_pool)
    # Fast fail check on import if we are in production
    if os.getenv("APP_ENV", "local") != "local":
        redis_client.ping()
        logger.info("Successfully initialized centralized Redis pool.")
except Exception as e:
    from urllib.parse import urlparse
    safe_url = REDIS_URL
    try:
        parsed = urlparse(REDIS_URL)
        safe_url = f"{parsed.scheme}://{parsed.hostname or 'localhost'}"
        if parsed.port:
            safe_url += f":{parsed.port}"
        if parsed.path:
            safe_url += parsed.path
    except Exception:
        safe_url = "[REDACTED]"
    logger.error(f"Failed to initialize Redis pool at {safe_url}: {e}")
    redis_client = None

from typing import Optional

def get_redis_client() -> Optional[redis.Redis]:
    """Returns the centralized Redis client instance."""
    return redis_client
