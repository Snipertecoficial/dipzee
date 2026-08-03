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
and the rest of that rotation family is revoked as a precaution without
logging out independent devices.
"""
import hashlib
import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from pymongo import ReturnDocument

from database import db

REFRESH_TOKEN_EXPIRE_DAYS = int(os.environ.get("REFRESH_TOKEN_EXPIRE_DAYS", "30"))


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def issue(
    user_id: str,
    *,
    mfa_verified: bool = False,
    family_id: str | None = None,
) -> str:
    raw = secrets.token_urlsafe(48)
    now = _now()
    family_id = family_id or str(uuid.uuid4())
    await db.refresh_tokens.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "family_id": family_id,
        "token_hash": _hash(raw),
        "created_at": now.isoformat(),
        "expires_at": (now + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)).isoformat(),
        "purge_at": now + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS + 1),
        "revoked_at": None,
        "mfa_verified": bool(mfa_verified),
    })
    return raw


async def rotate(raw_token: str) -> Optional[tuple]:
    """Validate + revoke the presented token and issue a new one.

    Returns ``(user_id, new_raw_token, mfa_verified)``, or ``None``.
    """
    token_hash = _hash(raw_token)
    now = _now()
    # Atomically claim the token. Exactly one concurrent request can change a
    # live row from revoked_at=None, so only that request may issue a successor.
    doc = await db.refresh_tokens.find_one_and_update(
        {"token_hash": token_hash, "revoked_at": None},
        {"$set": {"revoked_at": now.isoformat()}},
        return_document=ReturnDocument.BEFORE,
    )
    if not doc:
        reused = await db.refresh_tokens.find_one({"token_hash": token_hash})
        if reused and reused.get("revoked_at"):
            await revoke_family(reused["user_id"], reused.get("family_id"))
        return None

    if doc.get("revoked_at"):
        # Reuse of an already-rotated/revoked token — treat as theft and
        # kill every session for this user rather than trusting it.
        await revoke_family(doc["user_id"], doc.get("family_id"))
        return None

    expires_at = datetime.fromisoformat(doc["expires_at"])
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if now > expires_at:
        return None
    mfa_verified = bool(doc.get("mfa_verified", False))
    new_token = await issue(
        doc["user_id"],
        mfa_verified=mfa_verified,
        family_id=doc.get("family_id"),
    )
    return doc["user_id"], new_token, mfa_verified


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


async def revoke_family(user_id: str, family_id: str | None) -> None:
    """Revoke only the rotation chain proven compromised by a replay."""
    if not family_id:
        # Legacy rows predate token families. They cannot be linked safely, so
        # revoking that user's sessions remains the conservative fallback.
        await revoke_all(user_id)
        return
    await db.refresh_tokens.update_many(
        {"user_id": user_id, "family_id": family_id, "revoked_at": None},
        {"$set": {"revoked_at": _now().isoformat()}},
    )


async def count_active(user_id: str) -> int:
    return await db.refresh_tokens.count_documents({
        "user_id": user_id,
        "revoked_at": None,
        "expires_at": {"$gt": _now().isoformat()},
    })
