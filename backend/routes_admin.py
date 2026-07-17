"""Superadmin management panel routes. All endpoints require role=superadmin."""
import logging
import os
import re
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional

from database import db
from security import get_current_user, hash_password
from scoring import SETTINGS
from asset_service import refresh_asset
from routes_billing import cancel_subscription_silently, reconcile_pending_transactions, refund_transaction_charge
import refresh_tokens

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["admin"])

VALID_PLANS = {"none", "starter", "pro", "investor"}
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
        # Escaped and length-capped so a search term can't be used as a
        # catastrophic-backtracking regex (ReDoS) against every user's email.
        query = {"email": {"$regex": re.escape(q.strip()[:100]), "$options": "i"}}
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
    if body.password:
        # An admin-set password means the old one may be compromised (or the
        # user locked out) — kill existing sessions so a stale token can't
        # keep using the account under the old credentials.
        await refresh_tokens.revoke_all(user_id)
    fresh = await db.users.find_one({"id": user_id}, {"_id": 0, "hashed_password": 0})
    return fresh


@router.post("/users/{user_id}/revoke-sessions")
async def revoke_user_sessions(user_id: str, admin: dict = Depends(get_superadmin)):
    """Force-logout every device/session for a user (suspected compromise,
    offboarding a team member, etc.) without touching their account otherwise."""
    target = await db.users.find_one({"id": user_id})
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    await refresh_tokens.revoke_all(user_id)
    return {"ok": True}


@router.delete("/users/{user_id}")
async def delete_user(user_id: str, admin: dict = Depends(get_superadmin)):
    target = await db.users.find_one({"id": user_id})
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if target.get("role") == "superadmin":
        raise HTTPException(status_code=400, detail="Cannot delete a superadmin account")
    # Billing/payment records are kept for accounting/tax retention even after
    # the account is erased — only the subscription itself is stopped so the
    # customer is never charged again post-deletion.
    await cancel_subscription_silently(target.get("stripe_subscription_id"))
    await db.watchlist_items.delete_many({"user_id": user_id})
    await db.alerts.delete_many({"user_id": user_id})
    await db.alert_events.delete_many({"user_id": user_id})
    await db.positions.delete_many({"user_id": user_id})
    await db.password_resets.delete_many({"user_id": user_id})
    await db.refresh_tokens.delete_many({"user_id": user_id})
    await db.users.delete_one({"id": user_id})
    return {"ok": True}


@router.get("/assets")
async def list_assets(q: Optional[str] = None, admin: dict = Depends(get_superadmin)):
    query = {}
    if q:
        query = {"ticker": {"$regex": re.escape(q.strip()[:20].upper()), "$options": "i"}}
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
    from screener_service import refresh_universe, RefreshCooldownError
    try:
        count = await refresh_universe(limit=limit)
    except RefreshCooldownError as e:
        raise HTTPException(
            status_code=429,
            detail={"message": f"Universe was just refreshed. Try again in {e.retry_after_seconds}s.", "retry_after": e.retry_after_seconds},
        )
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


@router.post("/billing/sync")
async def sync_billing(admin: dict = Depends(get_superadmin)):
    """Re-check every unprocessed transaction against Stripe directly.

    This is the manual/on-demand counterpart to the periodic scheduler job
    (see scheduler.py) — a transaction can otherwise get stuck showing
    "initiated" forever if the customer never returns to the app after
    paying and the webhook wasn't configured or was missed.
    """
    return await reconcile_pending_transactions()


@router.post("/billing/transactions/{transaction_id}/refund")
async def refund_transaction(transaction_id: str, admin: dict = Depends(get_superadmin)):
    tx = await db.payment_transactions.find_one({"id": transaction_id})
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    if tx.get("refunded"):
        raise HTTPException(status_code=400, detail="Already refunded")
    return await refund_transaction_charge(tx)


@router.get("/config")
async def config(admin: dict = Depends(get_superadmin)):
    from providers import get_provider
    return {
        "finnhub": bool(os.environ.get("FINNHUB_API_KEY")),
        "fmp": bool(os.environ.get("FMP_API_KEY")),
        "polygon": bool(os.environ.get("POLYGON_API_KEY")),
        "alphavantage": bool(os.environ.get("ALPHAVANTAGE_API_KEY")),
        "twelvedata": bool(os.environ.get("TWELVEDATA_API_KEY")),
        "marketstack": bool(os.environ.get("MARKETSTACK_API_KEY")),
        "stripe": bool(os.environ.get("STRIPE_API_KEY")),
        "resend": bool(os.environ.get("RESEND_API_KEY")),
        "provider": get_provider().name,
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


# --------------------------------------------------------------------------- #
# AI provider keys (OpenAI / Anthropic / Gemini) — managed from Admin > IA so
# ops can rotate keys without touching the server. Raw keys are never sent
# back to the client, only a masked preview, mirroring how Stripe et al. do it.
# --------------------------------------------------------------------------- #
from ai_providers import get_ai_settings

AI_FIELDS = {
    "openai": ("openai_api_key", "OPENAI_API_KEY", "openai_model", "OPENAI_MODEL", "gpt-4o"),
    "anthropic": ("anthropic_api_key", "ANTHROPIC_API_KEY", "anthropic_model", "ANTHROPIC_MODEL", "claude-opus-4-8"),
    "google": ("google_api_key", "GOOGLE_API_KEY", "gemini_model", "GEMINI_MODEL", ""),
}


class AiConfigIn(BaseModel):
    active_provider: Optional[str] = None
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    google_api_key: Optional[str] = None
    openai_model: Optional[str] = None
    anthropic_model: Optional[str] = None
    gemini_model: Optional[str] = None


def _mask_key(key: str) -> str:
    if len(key) <= 8:
        return "•" * len(key)
    return f"{key[:6]}…{key[-4:]}"


async def _ai_config_view() -> dict:
    settings = await get_ai_settings()
    providers = {}
    for name, (key_field, key_env, model_field, model_env, default_model) in AI_FIELDS.items():
        db_key = settings.get(key_field)
        env_key = os.environ.get(key_env)
        if db_key:
            source, masked = "admin", _mask_key(db_key)
        elif env_key:
            source, masked = "env", None
        else:
            source, masked = None, None
        providers[name] = {
            "configured": bool(db_key or env_key),
            "source": source,  # "admin" (DB, rotatable here) | "env" (.env, read-only here) | None
            "masked_key": masked,
            "model": settings.get(model_field) or os.environ.get(model_env) or default_model,
        }
    return {
        "active_provider": settings.get("active_provider") or os.environ.get("AI_PROVIDER", "anthropic"),
        "providers": providers,
    }


@router.get("/ai-config")
async def get_ai_config(admin: dict = Depends(get_superadmin)):
    return await _ai_config_view()


@router.put("/ai-config")
async def update_ai_config(body: AiConfigIn, admin: dict = Depends(get_superadmin)):
    doc = await db.app_settings.find_one({"id": "ai_providers"})
    value = (doc or {}).get("value") or {}
    for field, new_val in body.dict(exclude_unset=True).items():
        if new_val == "":
            value.pop(field, None)  # explicit empty string clears a previously-set key/model
        elif new_val is not None:
            value[field] = new_val
    await db.app_settings.update_one(
        {"id": "ai_providers"},
        {"$set": {"id": "ai_providers", "value": value, "updated_at": datetime.now(timezone.utc).isoformat()}},
        upsert=True,
    )
    return await _ai_config_view()


# NEW SCHEMAS
import uuid
import time
from datetime import timedelta

class AnnouncementIn(BaseModel):
    content: str
    type: str = "info"  # info, warning, success
    active: bool = True
    expires_at: Optional[str] = None

class PartnerAdIn(BaseModel):
    partner_name: str
    description: str
    target_url: str
    image_url: Optional[str] = None
    placement: str = "sidebar"  # sidebar, dashboard, asset_detail
    active: bool = True


# NEW ENDPOINTS FOR ADMIN OPERATIONS

@router.get("/announcements")
async def list_announcements(admin: dict = Depends(get_superadmin)):
    announcements = await db.announcements.find({}).sort("created_at", -1).to_list(100)
    return {"announcements": announcements}

@router.post("/announcements")
async def create_announcement(body: AnnouncementIn, admin: dict = Depends(get_superadmin)):
    doc = {
        "id": str(uuid.uuid4()),
        "content": body.content,
        "type": body.type,
        "active": body.active,
        "expires_at": body.expires_at,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.announcements.insert_one(doc)
    doc.pop("_id", None)
    return doc

@router.put("/announcements/{announcement_id}")
async def update_announcement(announcement_id: str, body: AnnouncementIn, admin: dict = Depends(get_superadmin)):
    existing = await db.announcements.find_one({"id": announcement_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Announcement not found")
    updates = {
        "content": body.content,
        "type": body.type,
        "active": body.active,
        "expires_at": body.expires_at,
    }
    await db.announcements.update_one({"id": announcement_id}, {"$set": updates})
    fresh = await db.announcements.find_one({"id": announcement_id})
    return _clean(fresh)

@router.delete("/announcements/{announcement_id}")
async def delete_announcement(announcement_id: str, admin: dict = Depends(get_superadmin)):
    await db.announcements.delete_one({"id": announcement_id})
    return {"ok": True}

@router.get("/partner-ads")
async def list_partner_ads(admin: dict = Depends(get_superadmin)):
    ads = await db.partner_ads.find({}).sort("created_at", -1).to_list(100)
    return {"ads": ads}

@router.post("/partner-ads")
async def create_partner_ad(body: PartnerAdIn, admin: dict = Depends(get_superadmin)):
    doc = {
        "id": str(uuid.uuid4()),
        "partner_name": body.partner_name,
        "description": body.description,
        "target_url": body.target_url,
        "image_url": body.image_url,
        "placement": body.placement,
        "active": body.active,
        "clicks": 0,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.partner_ads.insert_one(doc)
    doc.pop("_id", None)
    return doc

@router.put("/partner-ads/{ad_id}")
async def update_partner_ad(ad_id: str, body: PartnerAdIn, admin: dict = Depends(get_superadmin)):
    existing = await db.partner_ads.find_one({"id": ad_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Ad not found")
    updates = {
        "partner_name": body.partner_name,
        "description": body.description,
        "target_url": body.target_url,
        "image_url": body.image_url,
        "placement": body.placement,
        "active": body.active,
    }
    await db.partner_ads.update_one({"id": ad_id}, {"$set": updates})
    fresh = await db.partner_ads.find_one({"id": ad_id})
    return _clean(fresh)

@router.delete("/partner-ads/{ad_id}")
async def delete_partner_ad(ad_id: str, admin: dict = Depends(get_superadmin)):
    await db.partner_ads.delete_one({"id": ad_id})
    return {"ok": True}

@router.get("/health")
async def system_health(admin: dict = Depends(get_superadmin)):
    db_ok = False
    db_latency = 0.0
    try:
        t0 = time.time()
        await db.command("ping")
        db_latency = (time.time() - t0) * 1000
        db_ok = True
    except Exception as e:
        logger.warning("DB health check failed: %s", e)
    
    # Scheduler check
    from scheduler import is_scheduler_running
    scheduler_running = is_scheduler_running()
    
    from providers import get_provider

    return {
        "db_connected": db_ok,
        "db_latency_ms": round(db_latency, 2),
        "scheduler_running": scheduler_running,
        "finnhub_key_present": bool(os.environ.get("FINNHUB_API_KEY")),
        "fmp_key_present": bool(os.environ.get("FMP_API_KEY")),
        "polygon_key_present": bool(os.environ.get("POLYGON_API_KEY")),
        "alphavantage_key_present": bool(os.environ.get("ALPHAVANTAGE_API_KEY")),
        "twelvedata_key_present": bool(os.environ.get("TWELVEDATA_API_KEY")),
        "marketstack_key_present": bool(os.environ.get("MARKETSTACK_API_KEY")),
        "stripe_key_present": bool(os.environ.get("STRIPE_API_KEY")),
        "resend_key_present": bool(os.environ.get("RESEND_API_KEY")),
        "provider": get_provider().name,
    }

@router.get("/stats/charts")
async def stats_charts(admin: dict = Depends(get_superadmin)):
    now_dt = datetime.now(timezone.utc)
    dates = [(now_dt - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(14, -1, -1)]
    
    # Real signups
    real_signups = {}
    users = await db.users.find({}, {"created_at": 1}).to_list(1000)
    for u in users:
        c_at = u.get("created_at")
        if c_at:
            try:
                dt_str = c_at.split("T")[0]
                real_signups[dt_str] = real_signups.get(dt_str, 0) + 1
            except Exception:
                pass

    # Real revenue
    real_rev = {}
    txs = await db.payment_transactions.find({"processed": True}, {"amount": 1, "created_at": 1}).to_list(1000)
    for tx in txs:
        c_at = tx.get("created_at")
        amount = tx.get("amount") or 0.0
        if c_at:
            try:
                dt_str = c_at.split("T")[0]
                real_rev[dt_str] = real_rev.get(dt_str, 0.0) + float(amount)
            except Exception:
                pass

    chart_data = []
    cumulative = 0.0

    for d in dates:
        signups = real_signups.get(d, 0)
        rev = real_rev.get(d, 0.0)

        cumulative += rev
        chart_data.append({
            "date": d,
            "signups": signups,
            "revenue": round(rev, 2),
            "cumulative": round(cumulative, 2),
        })

    return {"chart_data": chart_data}

