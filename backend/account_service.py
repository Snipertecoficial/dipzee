"""Central account export/erasure boundary shared by user and admin routes."""
import uuid

from dataset_service import anon_subject, purge_user


_ERASE_COLLECTIONS = (
    "watchlist_items",
    "alerts",
    "alert_events",
    "positions",
    "password_resets",
    "refresh_tokens",
)


async def export_account_data(db, user: dict) -> dict:
    user_id = user["id"]
    projection = {"_id": 0}
    result = {
        "profile": await db.users.find_one(
            {"id": user_id},
            {
                "_id": 0,
                "hashed_password": 0,
                "auth_version": 0,
                "mfa_secret": 0,
                "mfa_pending_secret": 0,
            },
        ),
    }
    for output_name, collection_name in (
        ("watchlist", "watchlist_items"),
        ("alerts", "alerts"),
        ("alert_events", "alert_events"),
        ("portfolio_positions", "positions"),
        ("payment_transactions", "payment_transactions"),
        ("billing_subscriptions", "billing_subscriptions"),
        ("billing_subscription_events", "billing_subscription_events"),
    ):
        result[output_name] = await db[collection_name].find(
            {"user_id": user_id}, projection,
        ).sort("created_at", -1).to_list(10000)
    anonymous_id = anon_subject(user_id)
    result["inference_log"] = await db.inference_log.find({"anon": anonymous_id}, projection).to_list(10000)
    result["decision_log"] = await db.decision_log.find({"anon": anonymous_id}, projection).to_list(10000)
    return result


async def erase_account_data(db, user: dict) -> None:
    """Idempotently erase personal data and anonymize retained accounting rows."""
    user_id = user["id"]
    for collection_name in _ERASE_COLLECTIONS:
        await db[collection_name].delete_many({"user_id": user_id})
    if user.get("email"):
        await db.login_attempts.delete_one({"_id": user["email"].strip().lower()})
    await purge_user(db, user_id)

    tombstone = f"deleted:{uuid.uuid4()}"
    retained_update = {
        "$set": {"user_id": tombstone, "account_erased": True},
        "$unset": {"email": "", "checkout_url": ""},
    }
    for collection_name in (
        "payment_transactions",
        "billing_subscriptions",
        "billing_subscription_events",
        "billing_outbox",
    ):
        await db[collection_name].update_many({"user_id": user_id}, retained_update)
    # Delete the identity last so a partially failed erasure can be retried.
    await db.users.delete_one({"id": user_id})
