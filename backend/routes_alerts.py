"""Alerts + notifications routes."""
import asyncio
import math
import os
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from asset_service import refresh_asset
from database import db
from plans import has_feature, limit_for
from security import require_feature
from notify_service import telegram_configured, send_telegram_message
from operation_lock import user_operation_lock

router = APIRouter(tags=["alerts"])

VALID_TYPES = {
    "buy_zone", "sell_zone", "target_reached", "price_below", "price_above",
    "score_threshold", "dividend_change", "daily_drop", "news",
}


class AlertIn(BaseModel):
    ticker: str
    type: str
    params: dict = Field(default_factory=dict)


class AlertUpdate(BaseModel):
    active: Optional[bool] = None
    params: Optional[dict] = None


def _validate_params(alert_type: str, raw: Optional[dict]) -> dict:
    params = dict(raw or {})
    if alert_type in {"price_below", "price_above"}:
        value = params.get("value")
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
            raise HTTPException(status_code=422, detail="Price alert value must be greater than zero")
        return {"value": float(value)}
    if alert_type == "score_threshold":
        value = params.get("value")
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= 100:
            raise HTTPException(status_code=422, detail="Score threshold must be between 0 and 100")
        return {"value": float(value)}
    if alert_type == "daily_drop":
        value = params.get("value", 5)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 < value <= 100:
            raise HTTPException(status_code=422, detail="Daily drop must be greater than 0 and at most 100 percent")
        return {"value": float(value)}
    # All other alert types are parameterless from the client's perspective.
    if params:
        raise HTTPException(status_code=422, detail="This alert type does not accept parameters")
    return {}


@router.get("/alerts")
async def list_alerts(user: dict = Depends(require_feature("alerts"))):
    items = await db.alerts.find({"user_id": user["id"]}, {"_id": 0}).to_list(500)
    items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return items


@router.post("/alerts")
async def create_alert(body: AlertIn, user: dict = Depends(require_feature("alerts"))):
    if body.type not in VALID_TYPES:
        raise HTTPException(status_code=400, detail="Invalid alert type")
    from asset_service import normalize_ticker
    try:
        ticker = normalize_ticker(body.ticker)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid ticker")

    # Ensure the asset exists so the engine can evaluate it.
    if not await refresh_asset(ticker):
        raise HTTPException(status_code=404, detail=f"No data available for {ticker}")

    params = _validate_params(body.type, body.params)
    if body.type == "news":
        # Only notify about news published after the alert is created.
        params = dict(params)
        params["since"] = int(datetime.now(timezone.utc).timestamp())

    alert = {
        "id": str(uuid.uuid4()),
        "user_id": user["id"],
        "ticker": ticker,
        "type": body.type,
        "params": params,
        "active": True,
        "last_triggered_at": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    async with user_operation_lock(db, "alert-create", user["id"]):
        fresh_user = await db.users.find_one({"id": user["id"]})
        if not fresh_user or not has_feature(fresh_user.get("plan"), "alerts"):
            raise HTTPException(status_code=403, detail="Alert access is no longer active")
        limit = limit_for(fresh_user.get("plan", "none"), "alerts")
        if limit is not None:
            active_count = await db.alerts.count_documents({"user_id": user["id"], "active": True})
            if active_count >= limit:
                raise HTTPException(
                    status_code=403,
                    detail={"code": "alert_limit", "limit": limit, "message": f"Your plan allows {limit} active alerts. Upgrade for unlimited alerts."},
                )
        await db.alerts.insert_one(alert)
    # Anonymized interest signal for the proprietary dataset (L5).
    from dataset_service import log_decision
    await log_decision(db, "alert_create", ticker, user=user, meta={"type": body.type})
    alert.pop("_id", None)
    return alert


@router.put("/alerts/{alert_id}")
async def update_alert(alert_id: str, body: AlertUpdate, user: dict = Depends(require_feature("alerts"))):
    alert = await db.alerts.find_one({"id": alert_id, "user_id": user["id"]})
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    updates = {}
    if body.active is not None:
        # Enforce active-alert limit when re-activating on Free plan.
        if body.active and not alert.get("active"):
            async with user_operation_lock(db, "alert-create", user["id"]):
                fresh_user = await db.users.find_one({"id": user["id"]})
                if not fresh_user or not has_feature(fresh_user.get("plan"), "alerts"):
                    raise HTTPException(status_code=403, detail="Alert access is no longer active")
                limit = limit_for(fresh_user.get("plan", "none"), "alerts")
                if limit is not None:
                    active_count = await db.alerts.count_documents({"user_id": user["id"], "active": True})
                    if active_count >= limit:
                        raise HTTPException(status_code=403, detail={"code": "alert_limit", "limit": limit, "message": f"Your plan allows {limit} active alerts."})
                await db.alerts.update_one(
                    {"id": alert_id, "user_id": user["id"]},
                    {"$set": {"active": True}},
                )
        else:
            updates["active"] = body.active
    if body.params is not None:
        updates["params"] = _validate_params(alert["type"], body.params)
    if updates:
        await db.alerts.update_one({"id": alert_id, "user_id": user["id"]}, {"$set": updates})
    fresh = await db.alerts.find_one({"id": alert_id, "user_id": user["id"]}, {"_id": 0})
    return fresh


@router.delete("/alerts/{alert_id}")
async def delete_alert(alert_id: str, user: dict = Depends(require_feature("alerts"))):
    res = await db.alerts.delete_one({"id": alert_id, "user_id": user["id"]})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Alert not found")
    return {"ok": True}


@router.get("/notifications")
async def list_notifications(user: dict = Depends(require_feature("in_app_alerts"))):
    visible = {"user_id": user["id"], "hidden": {"$ne": True}}
    events = await db.alert_events.find(visible, {"_id": 0}).sort("created_at", -1).to_list(200)
    unread = await db.alert_events.count_documents({**visible, "read": False})
    return {"events": events, "unread": unread}


@router.post("/notifications/{event_id}/read")
async def mark_read(event_id: str, user: dict = Depends(require_feature("in_app_alerts"))):
    await db.alert_events.update_one({"id": event_id, "user_id": user["id"]}, {"$set": {"read": True}})
    return {"ok": True}


@router.post("/notifications/read-all")
async def mark_all_read(user: dict = Depends(require_feature("in_app_alerts"))):
    await db.alert_events.update_many({"user_id": user["id"], "read": False}, {"$set": {"read": True}})
    return {"ok": True}


@router.get("/notifications/config")
async def notifications_config(user: dict = Depends(require_feature("alerts"))):
    """Which alert channels/types are actually available server-side, so the UI
    doesn't offer (and let users configure) a channel that will never fire —
    e.g. Telegram without a bot token, or 'news' alerts without a news key."""
    return {
        "telegram_configured": telegram_configured(),
        "news_available": bool(os.environ.get("FINNHUB_API_KEY")),
    }


@router.post("/notifications/telegram/test")
async def test_telegram(user: dict = Depends(require_feature("messaging_alerts"))):
    """Send a test message to the user's saved Telegram chat id, so they can
    confirm their setup works before relying on it for alerts."""
    if not telegram_configured():
        raise HTTPException(status_code=503, detail={"code": "telegram_unconfigured", "message": "Telegram is not configured on the server."})
    chat_id = (user.get("telegram_chat_id") or "").strip()
    if not chat_id:
        raise HTTPException(status_code=400, detail={"code": "no_chat_id", "message": "Save your Telegram chat id first."})
    ok = await asyncio.to_thread(send_telegram_message, chat_id, "\U0001F4C8 Dipzee — your Telegram alerts are connected. ✅")
    if not ok:
        raise HTTPException(status_code=502, detail={"code": "send_failed", "message": "Could not send. Check your chat id and that you've started a chat with the bot."})
    return {"ok": True}
