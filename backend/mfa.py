"""RFC 6238 TOTP helpers for privileged-account step-up authentication."""
import base64
import hashlib
import hmac
import secrets
import struct
import time
from urllib.parse import quote


def generate_secret() -> str:
    return base64.b32encode(secrets.token_bytes(20)).decode("ascii").rstrip("=")


def _code(secret: str, counter: int) -> str:
    padded = secret.upper() + "=" * ((8 - len(secret) % 8) % 8)
    key = base64.b32decode(padded, casefold=True)
    digest = hmac.new(key, struct.pack(">Q", counter), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    value = struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7FFFFFFF
    return f"{value % 1_000_000:06d}"


def verify_totp(secret: str, candidate: str, *, now: int | None = None) -> bool:
    if not candidate or len(candidate) != 6 or not candidate.isdigit():
        return False
    counter = int(now if now is not None else time.time()) // 30
    return any(hmac.compare_digest(_code(secret, counter + drift), candidate) for drift in (-1, 0, 1))


def provisioning_uri(secret: str, email: str) -> str:
    label = quote(f"Dipzee:{email}", safe="")
    issuer = quote("Dipzee", safe="")
    return f"otpauth://totp/{label}?secret={secret}&issuer={issuer}&algorithm=SHA1&digits=6&period=30"
