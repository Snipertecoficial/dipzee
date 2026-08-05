"""Security layer: response headers + in-memory rate limiting.

No external dependencies (works in the managed environment). The rate limiter
is a per-process sliding window keyed by client IP + route bucket. It is a
pragmatic first line of defense (DoS / brute-force dampening), not a fully
distributed limiter — for multi-replica production, front it with an API
gateway / WAF as well.
"""
import time
import logging
import ipaddress
from collections import defaultdict, deque

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


def client_ip(request) -> str:
    """Best-effort client IP for per-user rate limiting.

    Forwarded headers are trusted ONLY when the immediate peer is our own
    reverse proxy — a private/loopback address. A client connecting directly
    can't be trusted to describe its own IP, so for such peers we key on the
    socket address and ignore any forwarded header it may have spoofed.

    Behind the proxy we key, in order of preference, on:
      1. ``X-Dipzee-Client-Ip`` — an explicit single-value header, used if the
         ingress is ever configured to set it (it isn't today).
      2. ``X-Forwarded-For`` — what Caddy actually sends. Caddy APPENDS the real
         peer it observed as the LAST entry, so that entry is the trustworthy,
         non-spoofable client IP (leading entries can be client-supplied).

    Reading the (nonexistent) X-Dipzee header alone collapsed every request onto
    the proxy's own IP — one shared rate-limit bucket for all users, i.e. a
    self-inflicted 429 storm. Honouring X-Forwarded-For restores per-user keys.
    """
    peer = request.client.host if request.client else None
    peer_private = False
    if peer:
        try:
            pip = ipaddress.ip_address(peer)
            peer_private = pip.is_private or pip.is_loopback
        except ValueError:
            peer_private = False

    if peer_private:
        explicit = request.headers.get("x-dipzee-client-ip")
        if explicit:
            try:
                return str(ipaddress.ip_address(explicit.strip()))
            except ValueError:
                pass
        xff = request.headers.get("x-forwarded-for")
        if xff:
            parts = [p.strip() for p in xff.split(",") if p.strip()]
            if parts:
                try:
                    return str(ipaddress.ip_address(parts[-1]))
                except ValueError:
                    return parts[-1]
    return peer or "unknown"


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
    ("/api/webhook/stripe", 600),
    # Sends an outbound Telegram message — keep well below the default so it
    # can't be used to spam (even though it only targets the caller's own chat).
    ("/api/notifications/telegram/test", 6),
    # Full DB dump — superadmin-only and trusted, but a stricter cap prevents a
    # runaway loop from hammering Mongo.
    ("/api/admin/backup/run", 6),
    # On-demand LSE ingestion spends real export budget — cap it hard even for
    # the trusted superadmin so a stuck retry can't drain the allowance.
    ("/api/admin/lse/ingest", 4),
    # LSE catalog import also spends export budget — same hard cap.
    ("/api/admin/catalog/import-lse", 4),
    # US catalog import fetches the Nasdaq Trader directory + bulk-upserts ~6k
    # rows; trusted but capped so a stuck retry can't hammer Mongo/the source.
    ("/api/admin/catalog/import-us", 6),
    # News correlation spends LLM tokens (one call per new headline) — cap it.
    ("/api/admin/events/correlate", 6),
    # Intelligence briefs make an LLM call on a cache miss / forced refresh.
    # Cached hits are cheap; this caps abuse of ?refresh=1 across the surface.
    ("/api/intel/", 60),
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
