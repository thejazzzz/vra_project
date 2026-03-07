from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request
import os
import ipaddress
import logging

logger = logging.getLogger(__name__)

TRUST_PROXY = os.getenv("TRUST_PROXY", "false").lower() == "true"

def get_real_ip(request: Request) -> str:
    """Helper to extract IP address considering potential proxies and spoofing."""
    if TRUST_PROXY:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            ip_str = forwarded.split(",")[0].strip()
            # Validate IP format
            try:
                ipaddress.ip_address(ip_str)
                return ip_str
            except ValueError:
                logger.warning(f"Invalid IP format in X-Forwarded-For: {ip_str}")
                
    # Fallback if not trusting proxy or invalid IP
    if request.client and request.client.host:
        return request.client.host
    return "127.0.0.1"

# If we are behind a proxy (like Nginx), we might want to get the IP from X-Forwarded-For
# get_real_ip handles proxy-aware IP extraction when TRUST_PROXY is enabled.
limiter = Limiter(key_func=get_real_ip)

