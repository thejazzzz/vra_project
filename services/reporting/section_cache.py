import json
import logging
from typing import Dict, Any, Optional
from services.infrastructure.redis_pool import get_redis_client

logger = logging.getLogger(__name__)

class SectionCache:
    """
    Phase 10: Section Cache.
    Temporarily stores generated sections in Redis to prevent regenerating
    expensive sections if a later step fails.
    """
    TTL = 86400

    @staticmethod
    def _get_key(session_id: str, key: str) -> str:
        import hashlib
        safe_session = "".join(c for c in session_id if c.isalnum() or c in ('-', '_'))
        safe_key = "".join(c for c in key if c.isalnum() or c in ('-', '_'))
        
        orig_concat = f"{session_id}:{key}".encode('utf-8')
        hash_suffix = hashlib.sha256(orig_concat).hexdigest()[:8]
        
        if not safe_session: safe_session = "empty"
        if not safe_key: safe_key = "empty"
            
        return f"section_cache:{safe_session}:{safe_key}:{hash_suffix}"

    @staticmethod
    def get(session_id: str, key: str) -> Optional[Dict[str, Any]]:
        redis_client = get_redis_client()
        if not redis_client:
            return None
        cache_key = SectionCache._get_key(session_id, key)
        try:
            data = redis_client.get(cache_key)
            if data:
                result = json.loads(data)
                if isinstance(result, dict):
                    return result
                else:
                    logger.warning(f"Redis Cache read returned non-dict for {cache_key}")
                    return None
        except Exception as e:
            logger.warning(f"Redis Cache read failed for {cache_key}: {e}")
        return None

    @staticmethod
    def set(session_id: str, key: str, data: Dict[str, Any]):
        redis_client = get_redis_client()
        if not redis_client:
            logger.warning("Redis client not connected. Skipping cache set.")
            return
        cache_key = SectionCache._get_key(session_id, key)
        try:
            redis_client.setex(cache_key, SectionCache.TTL, json.dumps(data))
        except Exception as e:
            logger.warning(f"Redis Cache write failed for {cache_key}: {e}")
