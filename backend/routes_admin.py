"""Superadmin management panel routes. All endpoints require role=superadmin."""
import logging
import os
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional

from database import db
from security import get_current_user, hash_password
from scoring import SETTINGS
from asset_service import refresh_asset

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["admin"])

VALID_PLANS = {"free", "pro", "investor"}
VALID_ROLES = {"user", "superadmin"}


async def get_superadmin(user: dict = Depends(get_current_user)) -> dict:
    if user.get("role") != "superadmin":
        raise HTTPException(status_code=403, detail="Superadmin access required")
    return user


def _clean(doc: dict) -> dict:
    if not doc:
        return doc
    doc.pop("_id", None)
    doc.pop("hashed_password", None)
    return doc


@router.get("/stats")
async def stats(admin: dict = Depends(get_superadmin)):
    users_total = await db.users.count_documents({})
    plan_counts = {}
    for p in VALID_PLANS:
        plan_counts[p] = await db.users.count_documents({"plan": p})
    assets_total = await db.assets.count_documents({})
    alerts_total = await db.alerts.count_documents({})
    active_alerts = await db.alerts.count_documents({"active": True})
    events_total = await db.alert_events.count_documents({})
    watchlist_total = await db.watchlist_items.count_documents({})

    recent_users = await db.users.find({}, {"_id": 0, "hashed_password": 0}).sort("created_at", -1).to_list(6)

    # revenue from processed transactions
    revenue = 0.0
    tx_count = 0
    async for tx in db.payment_transactions.find({"processed": True}):
        revenue += float(tx.get("amount") or 0)
        tx_count += 1

    # top assets by score
    top_assets = await db.assets.find({"score": {"$ne": None}}, {"_id": 0}).sort("score", -1).to_list(5)

    return {
        "users_total": users_total,
        "plan_counts": plan_counts,
        "assets_total": assets_total,
        "alerts_total": alerts_total,
        "active_alerts": active_alerts,
        "events_total": events_total,
        "watchlist_total": watchlist_total,
        "revenue": round(revenue, 2),
        "paid_transactions": tx_count,
        "recent_users": recent_users,
        "top_assets": top_assets,
    }


@router.get("/users")
async def list_users(q: Optional[str] = None, admin: dict = Depends(get_superadmin)):
    query = {}
    if q:
        query = {"email": {"$regex": q, "$options": "i"}}
    users = await db.users.find(query, {"_id": 0, "hashed_password": 0}).sort("created_at", -1).to_list(500)
    # enrich with counts
    for u in users:
        u["watchlist_count"] = await db.watchlist_items.count_documents({"user_id": u["id"]})
        u["alerts_count"] = await db.alerts.count_documents({"user_id": u["id"]})
    return {"users": users, "count": len(users)}


class UserUpdate(BaseModel):
    plan: Optional[str] = None
    role: Optional[str] = None
    locale: Optional[str] = None
    currency: Optional[str] = None
    password: Optional[str] = None


@router.put("/users/{user_id}")
async def update_user(user_id: str, body: UserUpdate, admin: dict = Depends(get_superadmin)):
    target = await db.users.find_one({"id": user_id})
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    updates = {}
    if body.plan and body.plan in VALID_PLANS:
        updates["plan"] = body.plan
    if body.role and body.role in VALID_ROLES:
        updates["role"] = body.role
    if body.locale:
        updates["locale"] = body.locale
    if body.currency:
        updates["currency"] = body.currency
    if body.password:
        updates["hashed_password"] = hash_password(body.password)
    if updates:
        await db.users.update_one({"id": user_id}, {"$set": updates})
    fresh = await db.users.find_one({"id": user_id}, {"_id": 0, "hashed_password": 0})
    return fresh


@router.delete("/users/{user_id}")
async def delete_user(user_id: str, admin: dict = Depends(get_superadmin)):
    target = await db.users.find_one({"id": user_id})
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if target.get("role") == "superadmin":
        raise HTTPException(status_code=400, detail="Cannot delete a superadmin account")
    await db.watchlist_items.delete_many({"user_id": user_id})
    await db.alerts.delete_many({"user_id": user_id})
    await db.alert_events.delete_many({"user_id": user_id})
    await db.users.delete_one({"id": user_id})
    return {"ok": True}


@router.get("/assets")
async def list_assets(q: Optional[str] = None, admin: dict = Depends(get_superadmin)):
    query = {}
    if q:
        query = {"ticker": {"$regex": q.upper(), "$options": "i"}}
    assets = await db.assets.find(query, {"_id": 0}).sort("score", -1).to_list(500)
    return {"assets": assets, "count": len(assets)}


@router.post("/assets/refresh/{ticker}")
async def admin_refresh_asset(ticker: str, admin: dict = Depends(get_superadmin)):
    asset = await refresh_asset(ticker, force_target=True)
    if not asset:
        raise HTTPException(status_code=404, detail="No data")
    asset.pop("_id", None)
    return asset


@router.delete("/assets/{ticker}")
async def delete_asset(ticker: str, admin: dict = Depends(get_superadmin)):
    await db.assets.delete_one({"ticker": ticker.upper()})
    return {"ok": True}


@router.post("/universe/refresh")
async def universe_refresh(limit: Optional[int] = Query(None), admin: dict = Depends(get_superadmin)):
    from screener_service import refresh_universe
    count = await refresh_universe(limit=limit)
    return {"refreshed": count}


@router.post("/run-daily-refresh")
async def run_daily(admin: dict = Depends(get_superadmin)):
    from scheduler import daily_refresh_job
    await daily_refresh_job()
    return {"ok": True}


@router.get("/alerts")
async def all_alerts(admin: dict = Depends(get_superadmin)):
    alerts = await db.alerts.find({}, {"_id": 0}).sort("created_at", -1).to_list(500)
    # attach user email
    emails = {}
    for a in alerts:
        uid = a["user_id"]
        if uid not in emails:
            u = await db.users.find_one({"id": uid}, {"email": 1})
            emails[uid] = (u or {}).get("email", "?")
        a["user_email"] = emails[uid]
    return {"alerts": alerts, "count": len(alerts)}


@router.get("/events")
async def recent_events(admin: dict = Depends(get_superadmin)):
    events = await db.alert_events.find({}, {"_id": 0}).sort("created_at", -1).to_list(100)
    return {"events": events, "count": len(events)}


@router.get("/transactions")
async def transactions(admin: dict = Depends(get_superadmin)):
    txs = await db.payment_transactions.find({}, {"_id": 0}).sort("created_at", -1).to_list(200)
    return {"transactions": txs, "count": len(txs)}


@router.get("/config")
async def config(admin: dict = Depends(get_superadmin)):
    return {
        "finnhub": bool(os.environ.get("FINNHUB_API_KEY")),
        "fmp": bool(os.environ.get("FMP_API_KEY")),
        "stripe": bool(os.environ.get("STRIPE_API_KEY")),
        "resend": bool(os.environ.get("RESEND_API_KEY")),
        "provider": "finnhub" if os.environ.get("FINNHUB_API_KEY") else "yfinance",
    }


@router.get("/settings")
async def get_settings(admin: dict = Depends(get_superadmin)):
    return SETTINGS


class ScoringSettingsIn(BaseModel):
    weights: Optional[dict] = None
    upside: Optional[dict] = None
    income: Optional[dict] = None
    flags: Optional[dict] = None


@router.put("/settings")
async def update_settings(body: ScoringSettingsIn, admin: dict = Depends(get_superadmin)):
    # Mutate the shared SETTINGS dict IN PLACE so scoring picks up changes,
    # and persist to db.app_settings so it survives restarts.
    if body.weights:
        SETTINGS["weights"].update({k: float(v) for k, v in body.weights.items() if k in SETTINGS["weights"]})
    if body.upside:
        SETTINGS["upside"].update({k: float(v) for k, v in body.upside.items() if k in SETTINGS["upside"]})
    if body.income:
        SETTINGS["income"].update({k: float(v) for k, v in body.income.items() if k in SETTINGS["income"]})
    if body.flags:
        SETTINGS["flags"].update({k: float(v) for k, v in body.flags.items() if k in SETTINGS["flags"]})
    await db.app_settings.update_one(
        {"id": "scoring"},
        {"$set": {"id": "scoring", "value": {k: SETTINGS[k] for k in ("weights", "upside", "income", "flags")}, "updated_at": datetime.now(timezone.utc).isoformat()}},
        upsert=True,
    )
    return SETTINGS


async def load_scoring_settings():
    """Load persisted scoring settings at startup (mutate SETTINGS in place)."""
    doc = await db.app_settings.find_one({"id": "scoring"})
    if doc and doc.get("value"):
        for section in ("weights", "upside", "income", "flags"):
            if section in doc["value"] and isinstance(doc["value"][section], dict):
                SETTINGS[section].update(doc["value"][section])
        logger.info("Loaded persisted scoring settings.")
