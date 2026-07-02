"""Security layer: response headers + in-memory rate limiting.

No external dependencies (works in the managed environment). The rate limiter
is a per-process sliding window keyed by client IP + route bucket. It is a
pragmatic first line of defense (DoS / brute-force dampening), not a fully
distributed limiter — for multi-replica production, front it with an API
gateway / WAF as well.
"""
import time
import logging
from collections import defaultdict, deque

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


def client_ip(request) -> str:
    """Best-effort client IP, honouring the ingress' X-Forwarded-For."""
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Attach hardening headers to every response."""

    async def dispatch(self, request, call_next):
        resp = await call_next(request)
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        resp.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        resp.headers.setdefault(
            "Permissions-Policy", "geolocation=(), microphone=(), camera=(), payment=()"
        )
        # HSTS is safe behind the platform's TLS-terminating ingress.
        resp.headers.setdefault(
            "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
        )
        return resp


# --------------------------------------------------------------------------- #
# In-memory sliding-window rate limiter
# --------------------------------------------------------------------------- #
_WINDOW = 60  # seconds
_hits: dict = defaultdict(deque)  # key -> deque[timestamps]
_request_counter = 0

# Stricter per-IP limits on sensitive auth endpoints; generous default for
# normal authenticated app usage.
_LIMITS = (
    ("/api/auth/login", 12),
    ("/api/auth/register", 6),
    ("/api/auth/forgot", 6),
    ("/api/auth/reset", 6),
)
_DEFAULT_LIMIT = 300


def _bucket_for(path: str):
    for prefix, limit in _LIMITS:
        if path.startswith(prefix):
            return prefix, limit
    return "default", _DEFAULT_LIMIT


def _sweep(now: float) -> None:
    """Occasionally drop stale/empty deques to bound memory usage."""
    cutoff = now - _WINDOW
    stale = [k for k, dq in _hits.items() if not dq or dq[-1] < cutoff]
    for k in stale:
        _hits.pop(k, None)


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        global _request_counter
        path = request.url.path
        if not path.startswith("/api"):
            return await call_next(request)

        ip = client_ip(request)
        bucket, limit = _bucket_for(path)
        key = f"{ip}:{bucket}"
        now = time.time()

        _request_counter += 1
        if _request_counter % 500 == 0:
            _sweep(now)

        dq = _hits[key]
        cutoff = now - _WINDOW
        while dq and dq[0] < cutoff:
            dq.popleft()

        if len(dq) >= limit:
            retry = int(_WINDOW - (now - dq[0])) + 1
            logger.warning("rate limit exceeded ip=%s bucket=%s", ip, bucket)
            return JSONResponse(
                status_code=429,
                content={"detail": "Muitas requisições. Aguarde um instante e tente novamente."},
                headers={"Retry-After": str(max(retry, 1))},
            )

        dq.append(now)
        return await call_next(request)
