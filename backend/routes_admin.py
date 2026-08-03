"""Superadmin management panel routes. All endpoints require role=superadmin."""
import logging
import copy
import math
import os
import re
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field, field_validator
from typing import Optional

from database import db
from password_policy import validate_password_strength
from security import get_current_user, hash_password
from scoring import SETTINGS
from asset_service import refresh_asset
from routes_billing import cancel_subscription_for_deletion, reconcile_pending_transactions, refund_transaction_charge
from account_service import erase_account_data
import refresh_tokens

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["admin"])

VALID_PLANS = {"none", "starter", "pro", "investor"}
VALID_ROLES = {"user", "superadmin"}
SAFE_USER_PROJECTION = {
    "_id": 0,
    "hashed_password": 0,
    "auth_version": 0,
    "mfa_secret": 0,
    "mfa_pending_secret": 0,
}


async def get_superadmin(request: Request, user: dict = Depends(get_current_user)) -> dict:
    if user.get("role") != "superadmin":
        raise HTTPException(status_code=403, detail="Superadmin access required")
    mfa_required = os.environ.get(
        "ADMIN_MFA_REQUIRED",
        "true" if os.environ.get("ENV") == "production" else "false",
    ).lower() in {"1", "true", "yes"}
    if mfa_required and (not user.get("mfa_enabled") or not user.get("_session_mfa_verified")):
        raise HTTPException(
            status_code=403,
            detail={"code": "admin_mfa_required", "message": "Administrator MFA enrollment and verification are required"},
        )
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        from security_middleware import client_ip
        await db.admin_audit_log.insert_one({
            "id": str(uuid.uuid4()),
            "admin_id": user["id"],
            "method": request.method,
            "path": request.url.path,
            "client_ip": client_ip(request),
            "outcome": "attempted",
            "created_at": datetime.now(timezone.utc),
            "purge_at": datetime.now(timezone.utc) + timedelta(days=int(os.environ.get("ADMIN_AUDIT_RETENTION_DAYS", "365"))),
        })
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
    # Full browsable catalog (security_master) — the whole multi-exchange
    # universe (US + London), distinct from the ~250 scored/monitored assets.
    catalog_total = await db.security_master.count_documents({})
    catalog_us = await db.security_master.count_documents({"source": "us"})
    catalog_lse = await db.security_master.count_documents({"source": "lse"})
    alerts_total = await db.alerts.count_documents({})
    active_alerts = await db.alerts.count_documents({"active": True})
    events_total = await db.alert_events.count_documents({})
    watchlist_total = await db.watchlist_items.count_documents({})

    recent_users = await db.users.find({}, SAFE_USER_PROJECTION).sort("created_at", -1).to_list(6)

    # revenue from processed transactions
    revenue = 0.0
    tx_count = 0
    async for tx in db.payment_transactions.find({"processed": True}):
        revenue += int(tx.get("amount_cents") or 0) / 100
        tx_count += 1

    # top assets by score
    top_assets = await db.assets.find({"score": {"$ne": None}}, {"_id": 0}).sort("score", -1).to_list(5)

    return {
        "users_total": users_total,
        "plan_counts": plan_counts,
        "assets_total": assets_total,
        "catalog_total": catalog_total,
        "catalog_by_source": {"us": catalog_us, "lse": catalog_lse},
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
    users = await db.users.find(query, SAFE_USER_PROJECTION).sort("created_at", -1).to_list(500)
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

    _password = field_validator("password")(validate_password_strength)


@router.put("/users/{user_id}")
async def update_user(user_id: str, body: UserUpdate, admin: dict = Depends(get_superadmin)):
    target = await db.users.find_one({"id": user_id})
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    updates = {}
    if body.plan and body.plan in VALID_PLANS:
        updates["plan"] = body.plan
    if body.role and body.role in VALID_ROLES:
        if target.get("role") == "superadmin" and body.role != "superadmin":
            if target["id"] == admin["id"]:
                raise HTTPException(status_code=400, detail="You cannot demote your own superadmin account")
            if await db.users.count_documents({"role": "superadmin"}) <= 1:
                raise HTTPException(status_code=400, detail="At least one superadmin account is required")
        updates["role"] = body.role
    if body.locale:
        updates["locale"] = body.locale
    if body.currency:
        updates["currency"] = body.currency
    if body.password:
        updates["hashed_password"] = hash_password(body.password)
        updates["auth_version"] = int(target.get("auth_version", 0)) + 1
    if updates:
        await db.users.update_one({"id": user_id}, {"$set": updates})
    if body.password:
        # An admin-set password means the old one may be compromised (or the
        # user locked out) — kill existing sessions so a stale token can't
        # keep using the account under the old credentials.
        await refresh_tokens.revoke_all(user_id)
    fresh = await db.users.find_one({"id": user_id}, SAFE_USER_PROJECTION)
    return fresh


@router.post("/users/{user_id}/revoke-sessions")
async def revoke_user_sessions(user_id: str, admin: dict = Depends(get_superadmin)):
    """Force-logout every device/session for a user (suspected compromise,
    offboarding a team member, etc.) without touching their account otherwise."""
    target = await db.users.find_one({"id": user_id})
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    await refresh_tokens.revoke_all(user_id)
    await db.users.update_one({"id": user_id}, {"$inc": {"auth_version": 1}})
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
    await cancel_subscription_for_deletion(target.get("stripe_subscription_id"))
    await erase_account_data(db, target)
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


@router.post("/backup/run")
async def run_backup(admin: dict = Depends(get_superadmin)):
    """Trigger an on-demand database snapshot (the same one the scheduler runs
    daily) — local always, offsite if configured."""
    from backup_service import create_backup
    return await create_backup()


@router.get("/backup/status")
async def backup_status(admin: dict = Depends(get_superadmin)):
    """Recent local snapshots + whether offsite upload is configured."""
    from backup_service import list_local_backups
    return {
        "offsite_configured": bool(os.environ.get("BACKUP_S3_BUCKET") and os.environ.get("BACKUP_S3_ACCESS_KEY")),
        "recent": list_local_backups()[:10],
    }


@router.get("/backup/download")
async def download_backup(admin: dict = Depends(get_superadmin)):
    """Download the most recent authenticated encrypted backup snapshot.

    If no local snapshot exists yet, triggers a fresh one first.  Used by the
    local ``pull_production_db.py`` script to replicate the production database
    into a developer's localhost environment without SSH access."""
    from backup_service import list_local_backups, create_backup, BACKUP_DIR
    from fastapi.responses import FileResponse

    backups = list_local_backups()
    if not backups:
        await create_backup()
        backups = list_local_backups()
    if not backups:
        raise HTTPException(status_code=404, detail="No backup available")
    latest = backups[0]
    fpath = os.path.join(BACKUP_DIR, latest["file"])
    return FileResponse(
        fpath,
        media_type="application/octet-stream",
        filename=latest["file"],
    )


@router.get("/lse/status")
async def lse_status(admin: dict = Depends(get_superadmin)):
    """LSE health for the admin panel: configured?, vault export budget usage,
    this process's call count, and the last ingestion run."""
    import lse_service
    from lse_ingest import last_ingest
    return {
        "configured": lse_service.is_configured(),
        "raw_exposure": lse_service.client_raw_exposure_enabled(),
        "calls_last_hour": lse_service.local_calls_last_hour(),
        "max_calls_per_hour": lse_service.LSE_MAX_CALLS_PER_HOUR,
        "vault_usage": await lse_service.vault_usage(),
        "last_ingest": await last_ingest(),
    }


@router.post("/lse/ingest")
async def lse_ingest_now(admin: dict = Depends(get_superadmin)):
    """Trigger an on-demand LSE ingestion of the tracked universe (budget-aware,
    the same run the scheduler does daily). No-op when LSE isn't configured."""
    import lse_service
    if not lse_service.is_configured():
        raise HTTPException(status_code=503, detail="LSE is not configured")
    from lse_ingest import run_ingestion
    return await run_ingestion()


@router.get("/catalog/status")
async def catalog_status_route(admin: dict = Depends(get_superadmin)):
    """Security-master totals by source + last update, for the admin panel."""
    import security_master
    return await security_master.catalog_status()


@router.post("/catalog/import-us")
async def catalog_import_us(admin: dict = Depends(get_superadmin)):
    """(Re)import the US listed universe from the Nasdaq Trader directory."""
    import security_master
    return await security_master.import_us_listings(fetch=True)


@router.post("/catalog/import-lse")
async def catalog_import_lse(admin: dict = Depends(get_superadmin)):
    """Ingest the licensed LSE instrument catalog. No-op if LSE isn't configured."""
    import lse_service
    if not lse_service.is_configured():
        raise HTTPException(status_code=503, detail="LSE is not configured")
    import security_master
    return await security_master.import_lse_catalog()


@router.get("/kg/status")
async def kg_status(admin: dict = Depends(get_superadmin)):
    """Knowledge-graph size + node breakdown by kind."""
    from knowledge_graph import graph_status
    return await graph_status(db)


@router.post("/kg/rebuild")
async def kg_rebuild(admin: dict = Depends(get_superadmin)):
    """Rebuild the knowledge graph from curated seed + the assets collection."""
    from knowledge_graph import rebuild_graph
    return await rebuild_graph(db)


@router.get("/kg/affected/{kind}/{key}")
async def kg_affected(kind: str, key: str, admin: dict = Depends(get_superadmin)):
    """Preview: companies a macro/commodity/sector node propagates to (debug view)."""
    from knowledge_graph import node_id, affected_assets
    if kind not in ("macro", "commodity", "sector", "company"):
        raise HTTPException(status_code=400, detail="kind must be macro|commodity|sector|company")
    companies = await affected_assets(db, node_id(kind, key))
    return {"seed": node_id(kind, key), "count": len(companies), "companies": companies[:50]}


@router.post("/events/correlate")
async def events_correlate(limit: int = Query(15, ge=1, le=40), admin: dict = Depends(get_superadmin)):
    """On-demand: correlate fresh market news into enriched market_events."""
    from event_service import correlate_market_news
    return await correlate_market_news(db, limit=limit)


@router.get("/events/recent")
async def events_recent(symbol: Optional[str] = None, limit: int = Query(30, ge=1, le=100),
                        admin: dict = Depends(get_superadmin)):
    """Recent enriched events, optionally filtered to those affecting `symbol`."""
    from event_service import recent_events
    events = await recent_events(db, symbol=symbol, limit=limit)
    return {"count": len(events), "events": events}


@router.get("/dataset/status")
async def dataset_status_route(admin: dict = Depends(get_superadmin)):
    """Proprietary-dataset size (inferences/decisions) + retention window."""
    from dataset_service import dataset_status
    return await dataset_status(db)


@router.post("/dataset/prune")
async def dataset_prune_route(admin: dict = Depends(get_superadmin)):
    """Prune dataset rows past the retention window (the same the scheduler runs)."""
    from dataset_service import prune_old
    return await prune_old(db)


@router.post("/memory/index")
async def memory_index(admin: dict = Depends(get_superadmin)):
    """Backfill event_memory from market_events (vectors + resolved outcomes)."""
    from memory_service import index_events
    return await index_events(db)


@router.get("/memory/status")
async def memory_status_route(admin: dict = Depends(get_superadmin)):
    """Market-memory size + how many outcomes are resolved."""
    from memory_service import memory_status
    return await memory_status(db)


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

    model_config = {"extra": "forbid"}


def _validated_scoring_settings(patch: dict) -> dict:
    candidate = copy.deepcopy(SETTINGS)
    limits = {
        "weights": (0.0, 1.0),
        "upside": (0.0, 10.0),
        "income": (0.0, 1.0),
        "flags": (0.0, 1.0),
    }
    for section, values in patch.items():
        if section not in limits or not isinstance(values, dict):
            raise ValueError(f"Invalid scoring section: {section}")
        unknown = set(values) - set(candidate[section])
        if unknown:
            raise ValueError(f"Unknown {section} setting")
        lo, hi = limits[section]
        for key, raw in values.items():
            try:
                value = float(raw)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"{section}.{key} must be numeric") from exc
            if not math.isfinite(value) or value < lo or value > hi:
                raise ValueError(f"{section}.{key} is outside the allowed range")
            candidate[section][key] = value
    if abs(sum(candidate["weights"].values()) - 1.0) > 1e-6:
        raise ValueError("Scoring weights must sum to 1")
    if abs(candidate["upside"]["target_weight"] + candidate["upside"]["high_weight"] - 1.0) > 1e-6:
        raise ValueError("Upside weights must sum to 1")
    if candidate["upside"]["cap"] <= 0 or candidate["income"]["cap"] <= 0:
        raise ValueError("Scoring caps must be greater than zero")
    if candidate["flags"]["buy_zone_r"] >= candidate["flags"]["sell_zone_r"]:
        raise ValueError("Buy zone must be below sell zone")
    return candidate


@router.put("/settings")
async def update_settings(body: ScoringSettingsIn, admin: dict = Depends(get_superadmin)):
    # Mutate the shared SETTINGS dict IN PLACE so scoring picks up changes,
    # and persist to db.app_settings so it survives restarts.
    try:
        validated = _validated_scoring_settings(body.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    for section in ("weights", "upside", "income", "flags"):
        SETTINGS[section].clear()
        SETTINGS[section].update(validated[section])
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
        validated = _validated_scoring_settings(doc["value"])
        for section in ("weights", "upside", "income", "flags"):
            SETTINGS[section].clear()
            SETTINGS[section].update(validated[section])
        logger.info("Loaded persisted scoring settings.")


# --------------------------------------------------------------------------- #
# AI provider keys (OpenAI / Anthropic / Gemini) — managed from Admin > IA so
# ops can rotate keys without touching the server. Raw keys are never sent
# back to the client, only a masked preview, mirroring how Stripe et al. do it.
# --------------------------------------------------------------------------- #
from ai_providers import get_ai_settings
from secret_store import encrypt_secret

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
    for secret_field in ("openai_api_key", "anthropic_api_key", "google_api_key"):
        if value.get(secret_field):
            value[secret_field] = encrypt_secret(value[secret_field])
    await db.app_settings.update_one(
        {"id": "ai_providers"},
        {"$set": {"id": "ai_providers", "value": value, "updated_at": datetime.now(timezone.utc).isoformat()}},
        upsert=True,
    )
    return await _ai_config_view()


# NEW SCHEMAS
import time

class AnnouncementIn(BaseModel):
    content: str = Field(min_length=1, max_length=1000)
    type: str = "info"  # info, warning, success
    active: bool = True
    expires_at: Optional[str] = None

    @field_validator("type")
    @classmethod
    def valid_type(cls, value: str) -> str:
        if value not in {"info", "warning", "success"}:
            raise ValueError("Invalid announcement type")
        return value

class PartnerAdIn(BaseModel):
    partner_name: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=1, max_length=500)
    target_url: str = Field(max_length=500)
    image_url: Optional[str] = Field(default=None, max_length=500)
    placement: str = "sidebar"  # sidebar, dashboard, asset_detail
    active: bool = True

    @field_validator("target_url", "image_url")
    @classmethod
    def https_urls_only(cls, value: Optional[str]) -> Optional[str]:
        if value in (None, ""):
            return value
        from urllib.parse import urlparse
        parsed = urlparse(value)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("Only absolute HTTPS URLs without credentials are allowed")
        return value

    @field_validator("placement")
    @classmethod
    def valid_placement(cls, value: str) -> str:
        if value not in {"sidebar", "dashboard", "asset_detail"}:
            raise ValueError("Invalid ad placement")
        return value


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
    from email_service import is_really_configured as _email_is_really_configured

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
        # Distinct from mere presence: false when the key is the placeholder,
        # so a misconfigured email setup shows red instead of a false green.
        "email_configured": _email_is_really_configured(),
        "telegram_configured": bool(os.environ.get("TELEGRAM_BOT_TOKEN")),
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

