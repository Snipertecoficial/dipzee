"""Short Mongo-backed critical sections for cross-process quota enforcement."""
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError


@asynccontextmanager
async def user_operation_lock(db, scope: str, user_id: str, *, seconds: int = 30):
    lock_id = f"{scope}:{user_id}"
    token = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    await db.user_operation_locks.delete_one({"_id": lock_id, "expires_at": {"$lt": now}})
    try:
        await db.user_operation_locks.insert_one({
            "_id": lock_id,
            "token": token,
            "expires_at": now + timedelta(seconds=seconds),
        })
    except DuplicateKeyError:
        raise HTTPException(status_code=409, detail="Another account operation is already in progress")
    try:
        yield
    finally:
        await db.user_operation_locks.delete_one({"_id": lock_id, "token": token})
