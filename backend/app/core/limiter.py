from fastapi import Request
from slowapi import Limiter

from app.core.config import settings


def _get_client_ip(request: Request) -> str:
    """Extract the real client IP for rate-limit keying.

    Proxy headers (X-Real-IP, X-Forwarded-For) are only trusted when
    TRUST_PROXY_HEADERS=true — i.e. the app is known to sit behind a trusted
    reverse proxy (Railway, Fly, nginx). Without that guard a client with direct
    access to port 8000 can spoof any IP and bypass per-IP limits entirely.

    X-Real-IP is preferred because it is set by the proxy itself on both Fly
    and Railway and cannot be overridden by the client. X-Forwarded-For is a
    comma-separated hop chain the *client* can seed with arbitrary fake IPs
    (`X-Forwarded-For: 1.2.3.4`) — the leftmost entry is never trustworthy.
    Only the rightmost entry is guaranteed to have been appended by the
    trusted proxy itself, so that's the one we key on. The exact trustworthy
    position depends on how many proxies sit in front of the app — with more
    than one hop, prefer X-Real-IP or a platform-specific header over parsing
    X-Forwarded-For at all.
    """
    if settings.TRUST_PROXY_HEADERS:
        if real_ip := request.headers.get("X-Real-IP"):
            return real_ip
        if forwarded_for := request.headers.get("X-Forwarded-For"):
            return forwarded_for.split(",")[-1].strip()
    return request.client.host if request.client else "unknown"


limiter = Limiter(
    key_func=_get_client_ip,
    storage_uri=settings.REDIS_URL,
    default_limits=[f"{settings.RATE_LIMIT_PER_MINUTE}/minute"],
)
