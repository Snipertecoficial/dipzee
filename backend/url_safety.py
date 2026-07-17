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
import socket
from urllib.parse import urlparse


class UnsafeUrlError(ValueError):
    """Raised when a URL is missing, malformed, or targets a non-public host."""


def assert_safe_outbound_url(url: str) -> None:
    parsed = urlparse((url or "").strip())
    if parsed.scheme not in ("http", "https"):
        raise UnsafeUrlError("URL must start with http:// or https://")
    if not parsed.hostname:
        raise UnsafeUrlError("URL must include a host")

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
