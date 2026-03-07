import os
# Updated Redis configuration
import redis
import logging

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
IS_PRODUCTION = os.getenv("APP_ENV", "local") != "local"
REDIS_FAIL_CLOSED = os.getenv("REDIS_FAIL_CLOSED", "false").lower() == "true"

# Redis connection pool
try:
    redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    # Test connection on startup if in production
    if IS_PRODUCTION:
        redis_client.ping()
        logger.info("Successfully connected to Redis.")
except Exception as e:
    import urllib.parse
    parsed_url = urllib.parse.urlparse(REDIS_URL)
    if parsed_url.password and parsed_url.hostname:
        port_part = f":{parsed_url.port}" if parsed_url.port else ""
        sanitized_url = parsed_url._replace(netloc=f"{parsed_url.username or ''}:***@{parsed_url.hostname}{port_part}").geturl()
    else:
        sanitized_url = REDIS_URL
    logger.error(f"Failed to connect to Redis at {sanitized_url}: {e}")
    redis_client = None

def blocklist_token(jti: str, exp_timestamp: int):
    """
    Adds a JWT's unique ID to the blocklist.
    Automatically expires the key in Redis when the JWT itself expires.
    """
    if not redis_client:
        logger.warning(f"Redis not connected. Cannot blocklist token: {jti}")
        return
        
    import time
    ttl = int(exp_timestamp - time.time())
    if ttl > 0:
        try:
            redis_client.setex(f"blocklist:{jti}", ttl, "true")
        except Exception as e:
            logger.error(f"Failed to set blocklist in Redis: {e}")

def is_token_blocklisted(jti: str) -> bool:
    """Checks if a JWT's unique ID is currently in the blocklist."""
    if not redis_client:
        if REDIS_FAIL_CLOSED:
            logger.error("Redis client unavailable; treating token as blocklisted (fail-closed).")
            return True
        else:
            logger.warning("Redis client unavailable; allowing token (fail-open).")
            return False
    try:
        return redis_client.exists(f"blocklist:{jti}") == 1
    except Exception as e:
        logger.error(f"Redis blocklist check failed: {e}")
        return REDIS_FAIL_CLOSED

def record_failed_login(email: str, max_attempts: int = 5, lockout_seconds: int = 900) -> bool:
    """
    Records a failed login attempt.
    Returns True if the account is now locked out.
    """
    if not redis_client: 
        return REDIS_FAIL_CLOSED
        
    key = f"failed_login:{email.lower().strip()}"
    try:
        pipe = redis_client.pipeline()
        pipe.incr(key)
        pipe.expire(key, lockout_seconds)
        results = pipe.execute()
        attempts = results[0]
        return attempts >= max_attempts
    except Exception as e:
        logger.error(f"Redis failed login tracking error: {e}")
        return REDIS_FAIL_CLOSED

def is_account_locked(email: str, max_attempts: int = 5) -> bool:
    """Checks if an account is locked due to too many failed attempts."""
    if not redis_client:
        return REDIS_FAIL_CLOSED
        
    key = f"failed_login:{email.lower().strip()}"
    try:
        attempts = redis_client.get(key)
        if attempts is None:
            return False
        return int(attempts) >= max_attempts
    except ValueError:
        logger.warning(f"Invalid attempt count in Redis for key {key}, clearing")
        redis_client.delete(key)
        return False
    except Exception as e:
        logger.error(f"Redis lockout check error: {e}")
        return False

def clear_failed_login(email: str) -> None:
    """Clears failed login attempts after a successful login."""
    if not redis_client:
        return
    try:
        redis_client.delete(f"failed_login:{email.lower().strip()}")
    except Exception as e:
        logger.error(f"Redis failed login clear error: {e}")
