"""Preserve dataset subject continuity when moving off the legacy JWT salt."""
import hashlib
import os


def _subject(salt: str, user_id: str) -> str:
    return "u_" + hashlib.sha256(f"{salt}:{user_id}".encode("utf-8")).hexdigest()[:16]


async def up(db):
    legacy_salt = os.environ.get("JWT_SECRET", "")
    current_salt = os.environ.get("DATASET_SALT", "")
    if not legacy_salt or not current_salt:
        raise RuntimeError("JWT_SECRET and DATASET_SALT are required for pseudonym migration")
    if legacy_salt == current_salt:
        return

    async for user in db.users.find(
        {"id": {"$exists": True, "$nin": [None, ""]}},
        {"_id": 0, "id": 1},
    ):
        user_id = user.get("id")
        if not user_id:
            continue
        legacy_subject = _subject(legacy_salt, user_id)
        current_subject = _subject(current_salt, user_id)
        for collection_name in ("inference_log", "decision_log"):
            await db[collection_name].update_many(
                {"anon": legacy_subject},
                {"$set": {"anon": current_subject}},
            )
