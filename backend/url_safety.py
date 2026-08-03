"""SSRF guard for any URL the server fetches on a user's behalf.

Today that's only the alert webhook (``notify_service._send_webhook``), but
this stays generic for future outbound-URL features. Blocks non-http(s)
schemes and any hostname that resolves to a private, loopback, link-local, or
otherwise non-globally-routable address — including cloud metadata endpoints
(169.254.169.254) and internal Docker service names like ``mongo``/``backend``.

Applied at TWO points, not just one: when the user saves the URL (fail fast,
good UX) and again immediately before the server actually makes the request
(closes the DNS-rebinding/TOCTOU gap where a hostname resolves to a public IP
at save time but an internal one at delivery time).
"""
import ipaddress
import os
import socket
from urllib.parse import urlparse


class UnsafeUrlError(ValueError):
    """Raised when a URL is missing, malformed, or targets a non-public host."""


def _allowed_hosts() -> set[str]:
    return {h.strip().lower().rstrip(".") for h in os.environ.get("WEBHOOK_ALLOWED_HOSTS", "").split(",") if h.strip()}


def _host_allowed(hostname: str, allowed: set[str]) -> bool:
    host = hostname.lower().rstrip(".")
    for rule in allowed:
        if rule.startswith("*.") and host.endswith(rule[1:]) and host != rule[2:]:
            return True
        if host == rule:
            return True
    return False


def assert_safe_outbound_url(url: str) -> None:
    parsed = urlparse((url or "").strip())
    if parsed.scheme not in ("http", "https"):
        raise UnsafeUrlError("URL must start with http:// or https://")
    if not parsed.hostname:
        raise UnsafeUrlError("URL must include a host")
    if parsed.username or parsed.password:
        raise UnsafeUrlError("URL credentials are not allowed")

    allowed = _allowed_hosts()
    if os.environ.get("ENV", "development") == "production":
        if parsed.scheme != "https":
            raise UnsafeUrlError("Webhook URL must use HTTPS")
        if parsed.port not in (None, 443):
            raise UnsafeUrlError("Webhook URL must use the standard HTTPS port")
        # Arbitrary attacker-controlled DNS cannot be made rebinding-safe by a
        # resolve-then-request check. Production therefore permits only exact
        # operator-approved hosts (or explicit wildcard suffixes).
        if not allowed or not _host_allowed(parsed.hostname, allowed):
            raise UnsafeUrlError("Webhook host is not allowed")

    try:
        infos = socket.getaddrinfo(parsed.hostname, None)
    except socket.gaierror:
        raise UnsafeUrlError("Could not resolve host")

    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if (
            ip.is_private or ip.is_loopback or ip.is_link_local
            or ip.is_reserved or ip.is_multicast or ip.is_unspecified
        ):
            raise UnsafeUrlError("URL resolves to a non-public address")
