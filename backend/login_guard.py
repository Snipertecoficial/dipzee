"""Per-account brute-force protection backed by MongoDB.

Complements the IP-based rate limiter: this locks a specific account after too
many failed logins, which also defends against distributed/IP-rotating attacks.
Stores only counters and timestamps — never passwords.
"""
from datetime import datetime, timezone, timedelta

from pymongo import ReturnDocument

from database import db

MAX_FAILS = 5           # failed attempts before lockout
LOCK_MINUTES = 10       # lockout duration once the threshold is hit


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _norm(email: str) -> str:
    return (email or "").strip().lower()


async def check_locked(email: str):
    """Return (is_locked, seconds_remaining)."""
    key = _norm(email)
    if not key:
        return (False, 0)
    doc = await db.login_attempts.find_one({"_id": key})
    if not doc:
        return (False, 0)
    until = doc.get("locked_until")
    if not until:
        return (False, 0)
    try:
        dt = datetime.fromisoformat(until)
    except Exception:
        return (False, 0)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    remaining = (dt - _now()).total_seconds()
    return (True, int(remaining)) if remaining > 0 else (False, 0)


async def record_failure(email: str) -> None:
    key = _norm(email)
    if not key:
        return
    now = _now()
    doc = await db.login_attempts.find_one_and_update(
        {"_id": key},
        {"$inc": {"fails": 1}, "$set": {
            "last_fail": now.isoformat(),
            "purge_at": now + timedelta(days=1),
        }},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    fails = int((doc or {}).get("fails", 1))
    if fails >= MAX_FAILS:
        await db.login_attempts.update_one(
            {"_id": key},
            {"$set": {
                "locked_until": (now + timedelta(minutes=LOCK_MINUTES)).isoformat(),
                "fails": 0,
            }},
        )


async def record_success(email: str) -> None:
    key = _norm(email)
    if key:
        await db.login_attempts.delete_one({"_id": key})
