"""Normalize security/billing fields before enforcing critical indexes."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
import uuid


_ID_COLLECTIONS = (
    "users",
    "watchlist_items",
    "alerts",
    "alert_events",
    "positions",
    "refresh_tokens",
    "payment_transactions",
    "announcements",
    "partner_ads",
)


def _parse_datetime(value):
    if isinstance(value, datetime):
        result = value
    elif isinstance(value, str):
        try:
            result = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None
    if result.tzinfo is None:
        result = result.replace(tzinfo=timezone.utc)
    return result


async def _backfill_ids(db):
    for collection_name in _ID_COLLECTIONS:
        collection = db[collection_name]
        async for doc in collection.find(
            {"$or": [{"id": {"$exists": False}}, {"id": None}, {"id": ""}]},
            {"_id": 1},
        ):
            await collection.update_one(
                {"_id": doc["_id"]},
                {"$set": {"id": str(uuid.uuid4())}},
            )


async def _backfill_expiry(db, collection_name, source_field, retention_days=1):
    collection = db[collection_name]
    async for doc in collection.find(
        {"purge_at": {"$exists": False}, source_field: {"$exists": True}},
        {"_id": 1, source_field: 1},
    ):
        expires = _parse_datetime(doc.get(source_field))
        if expires:
            await collection.update_one(
                {"_id": doc["_id"]},
                {"$set": {"purge_at": expires + timedelta(days=retention_days)}},
            )


async def _assert_no_duplicates(db, collection_name, field):
    rows = await db[collection_name].aggregate([
        {"$match": {field: {"$exists": True, "$nin": [None, ""]}}},
        {"$group": {"_id": f"${field}", "count": {"$sum": 1}}},
        {"$match": {"count": {"$gt": 1}}},
        {"$limit": 1},
    ]).to_list(1)
    if rows:
        # Deliberately do not include the duplicate value in logs/errors.
        raise RuntimeError(f"duplicate logical key detected: {collection_name}.{field}")


async def up(db):
    await _backfill_ids(db)
    await db.users.update_many(
        {"auth_version": {"$exists": False}},
        {"$set": {"auth_version": 0}},
    )
    await _backfill_expiry(db, "password_resets", "expires_at")
    await _backfill_expiry(db, "refresh_tokens", "expires_at")

    async for tx in db.payment_transactions.find(
        {"amount_cents": {"$exists": False}, "amount": {"$exists": True}},
        {"_id": 1, "amount": 1},
    ):
        try:
            cents = int((Decimal(str(tx["amount"])) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
        except Exception:
            continue
        await db.payment_transactions.update_one(
            {"_id": tx["_id"]},
            {"$set": {"amount_cents": cents}, "$unset": {"amount": ""}},
        )

    # Older Polygon image URLs embedded API keys. Remove the cached URL so it
    # is rebuilt through a client-safe provider path without exposing secrets.
    await db.assets.update_many(
        {"logo": {"$regex": r"[?&](api_?key|token|key)=", "$options": "i"}},
        {"$unset": {"logo": ""}},
    )

    for collection_name, field in (
        ("users", "id"),
        ("users", "email"),
        ("watchlist_items", "id"),
        ("alerts", "id"),
        ("alert_events", "id"),
        ("positions", "id"),
        ("refresh_tokens", "id"),
        ("refresh_tokens", "token_hash"),
        ("password_resets", "token_hash"),
        ("payment_transactions", "id"),
        ("stripe_events", "event_id"),
        ("billing_subscriptions", "stripe_subscription_id"),
    ):
        await _assert_no_duplicates(db, collection_name, field)

    # The historical non-sparse index allowed only one transaction without a
    # session_id. Replace it with the explicitly named sparse index at startup.
    index_info = await db.payment_transactions.index_information()
    old = index_info.get("session_id_1")
    if old and old.get("unique") and not old.get("sparse"):
        await db.payment_transactions.drop_index("session_id_1")

    # These indexes existed as non-unique definitions in the previous schema.
    # After the duplicate check above, remove the incompatible definitions so
    # startup can recreate them with the required uniqueness.
    for collection_name in ("password_resets", "refresh_tokens"):
        collection = db[collection_name]
        index_info = await collection.index_information()
        old = index_info.get("token_hash_1")
        if old and not old.get("unique"):
            await collection.drop_index("token_hash_1")

    ai_doc = await db.app_settings.find_one({"id": "ai_providers"})
    if ai_doc and isinstance(ai_doc.get("value"), dict):
        from secret_store import encrypt_secret, is_encrypted_secret
        settings = dict(ai_doc["value"])
        changed = False
        for field in ("openai_api_key", "anthropic_api_key", "google_api_key"):
            value = settings.get(field)
            if value and not is_encrypted_secret(value):
                settings[field] = encrypt_secret(value)
                changed = True
        if changed:
            await db.app_settings.update_one(
                {"_id": ai_doc["_id"]},
                {"$set": {"value": settings}},
            )
