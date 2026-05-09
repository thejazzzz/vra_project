import logging
import random
import time
from typing import Optional

from services.infrastructure.redis_pool import get_redis_client

logger = logging.getLogger(__name__)


_RATE_LIMIT_LUA = r"""
-- KEYS[1] = key
-- ARGV[1] = interval_ms (integer)
--
-- Stores the next allowed timestamp (ms since epoch) in Redis.
-- Returns:
--   0 if request is allowed now (and updates the next timestamp)
--   wait_ms (>0) if caller must wait that long

local key = KEYS[1]
local interval_ms = tonumber(ARGV[1])

local t = redis.call('TIME')
local now_ms = (tonumber(t[1]) * 1000) + math.floor(tonumber(t[2]) / 1000)

local next_ms = redis.call('GET', key)
if not next_ms then
  redis.call('SET', key, tostring(now_ms + interval_ms))
  return 0
end

next_ms = tonumber(next_ms)
if now_ms >= next_ms then
  redis.call('SET', key, tostring(now_ms + interval_ms))
  return 0
end

return next_ms - now_ms
"""


def wait_global_rps(
    key: str,
    requests_per_second: float = 1.0,
    *,
    timeout_seconds: float = 30.0,
    jitter_seconds_max: float = 0.1,
    redis_error_fail_open: bool = True,
) -> None:
    """
    Global (multi-process) rate limiter backed by Redis.

    Guarantees an average max of `requests_per_second` across all processes that
    share the same Redis and `key`.
    """
    if requests_per_second <= 0:
        return

    redis_client = get_redis_client()
    if not redis_client:
        return

    interval_ms = max(1, int(1000.0 / requests_per_second))
    start = time.monotonic()

    while True:
        try:
            wait_ms = redis_client.eval(_RATE_LIMIT_LUA, 1, key, interval_ms)
        except Exception as e:
            if redis_error_fail_open:
                logger.warning(f"Redis rate limiter unavailable; proceeding (fail-open). Error: {e}")
                return
            raise

        try:
            wait_ms_int = int(wait_ms)
        except Exception:
            wait_ms_int = 0

        if wait_ms_int <= 0:
            return

        sleep_s = (wait_ms_int / 1000.0) + random.uniform(0.0, max(0.0, jitter_seconds_max))
        if (time.monotonic() - start) + sleep_s > timeout_seconds:
            logger.warning(
                f"Global rate limiter timeout after {timeout_seconds:.1f}s for key={key}; proceeding."
            )
            return

        time.sleep(sleep_s)

