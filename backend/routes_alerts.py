"""Alerts + notifications routes."""
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from asset_service import refresh_asset
from database import db
from plans import limit_for
from security import get_current_user

router = APIRouter(tags=["alerts"])

VALID_TYPES = {
    "buy_zone", "sell_zone", "target_reached", "price_below", "price_above",
    "score_threshold", "dividend_change", "daily_drop", "news",
}


class AlertIn(BaseModel):
    ticker: str
    type: str
    params: dict = {}


class AlertUpdate(BaseModel):
    active: Optional[bool] = None
    params: Optional[dict] = None


@router.get("/alerts")
async def list_alerts(user: dict = Depends(get_current_user)):
    items = await db.alerts.find({"user_id": user["id"]}, {"_id": 0}).to_list(500)
    items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return items


@router.post("/alerts")
async def create_alert(body: AlertIn, user: dict = Depends(get_current_user)):
    if body.type not in VALID_TYPES:
        raise HTTPException(status_code=400, detail="Invalid alert type")
    ticker = body.ticker.strip().upper()

    limit = limit_for(user.get("plan", "free"), "alerts")
    if limit is not None:
        active_count = await db.alerts.count_documents({"user_id": user["id"], "active": True})
        if active_count >= limit:
            raise HTTPException(
                status_code=403,
                detail={"code": "alert_limit", "limit": limit, "message": f"Free plan allows {limit} active alerts. Upgrade for unlimited alerts."},
            )

    # Ensure the asset exists so the engine can evaluate it.
    await refresh_asset(ticker)

    params = body.params or {}
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
    await db.alerts.insert_one(alert)
    alert.pop("_id", None)
    return alert


@router.put("/alerts/{alert_id}")
async def update_alert(alert_id: str, body: AlertUpdate, user: dict = Depends(get_current_user)):
    alert = await db.alerts.find_one({"id": alert_id, "user_id": user["id"]})
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    updates = {}
    if body.active is not None:
        # Enforce active-alert limit when re-activating on Free plan.
        if body.active and not alert.get("active"):
            limit = limit_for(user.get("plan", "free"), "alerts")
            if limit is not None:
                active_count = await db.alerts.count_documents({"user_id": user["id"], "active": True})
                if active_count >= limit:
                    raise HTTPException(status_code=403, detail={"code": "alert_limit", "limit": limit, "message": f"Free plan allows {limit} active alerts."})
        updates["active"] = body.active
    if body.params is not None:
        updates["params"] = body.params
    if updates:
        await db.alerts.update_one({"id": alert_id}, {"$set": updates})
    fresh = await db.alerts.find_one({"id": alert_id}, {"_id": 0})
    return fresh


@router.delete("/alerts/{alert_id}")
async def delete_alert(alert_id: str, user: dict = Depends(get_current_user)):
    res = await db.alerts.delete_one({"id": alert_id, "user_id": user["id"]})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Alert not found")
    return {"ok": True}


@router.get("/notifications")
async def list_notifications(user: dict = Depends(get_current_user)):
    events = await db.alert_events.find({"user_id": user["id"]}, {"_id": 0}).to_list(200)
    events.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    unread = sum(1 for e in events if not e.get("read"))
    return {"events": events, "unread": unread}


@router.post("/notifications/{event_id}/read")
async def mark_read(event_id: str, user: dict = Depends(get_current_user)):
    await db.alert_events.update_one({"id": event_id, "user_id": user["id"]}, {"$set": {"read": True}})
    return {"ok": True}


@router.post("/notifications/read-all")
async def mark_all_read(user: dict = Depends(get_current_user)):
    await db.alert_events.update_many({"user_id": user["id"], "read": False}, {"$set": {"read": True}})
    return {"ok": True}
