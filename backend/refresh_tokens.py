"""Revocable, server-side sessions layered on top of the short-lived
stateless JWT access token (see security.py).

Access tokens are intentionally short-lived (``ACCESS_TOKEN_EXPIRE_MINUTES``)
so a stolen one has a small blast radius. Refresh tokens are the opposite:
long-lived but revocable — each is just an opaque random string whose hash is
looked up in ``db.refresh_tokens``, so deleting/marking a row revoked takes
effect immediately, unlike a self-contained JWT which stays valid until it
expires no matter what the server does.

Rotated on every use (the presented token is revoked and a new one issued in
the same call), so a stolen-and-later-replayed refresh token is detectable:
if an already-REVOKED token is presented again, that's a signal of theft,
and every other token for that user is revoked as a precaution.
"""
import hashlib
import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from database import db

REFRESH_TOKEN_EXPIRE_DAYS = int(os.environ.get("REFRESH_TOKEN_EXPIRE_DAYS", "30"))


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def issue(user_id: str) -> str:
    raw = secrets.token_urlsafe(48)
    now = _now()
    await db.refresh_tokens.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "token_hash": _hash(raw),
        "created_at": now.isoformat(),
        "expires_at": (now + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)).isoformat(),
        "revoked_at": None,
    })
    return raw


async def rotate(raw_token: str) -> Optional[tuple]:
    """Validate + revoke the presented token and issue a new one.

    Returns ``(user_id, new_raw_token)``, or ``None`` if invalid/expired.
    """
    doc = await db.refresh_tokens.find_one({"token_hash": _hash(raw_token)})
    if not doc:
        return None

    if doc.get("revoked_at"):
        # Reuse of an already-rotated/revoked token — treat as theft and
        # kill every session for this user rather than trusting it.
        await revoke_all(doc["user_id"])
        return None

    expires_at = datetime.fromisoformat(doc["expires_at"])
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if _now() > expires_at:
        return None

    await db.refresh_tokens.update_one({"id": doc["id"]}, {"$set": {"revoked_at": _now().isoformat()}})
    new_token = await issue(doc["user_id"])
    return doc["user_id"], new_token


async def revoke(raw_token: str) -> None:
    await db.refresh_tokens.update_one(
        {"token_hash": _hash(raw_token), "revoked_at": None},
        {"$set": {"revoked_at": _now().isoformat()}},
    )


async def revoke_all(user_id: str) -> None:
    """Kill every active session for a user — used for 'log out everywhere',
    password changes/resets, and admin-initiated session revocation."""
    await db.refresh_tokens.update_many(
        {"user_id": user_id, "revoked_at": None},
        {"$set": {"revoked_at": _now().isoformat()}},
    )


async def count_active(user_id: str) -> int:
    return await db.refresh_tokens.count_documents({"user_id": user_id, "revoked_at": None})
