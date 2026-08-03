"""Dipzee FastAPI application entrypoint."""
import logging

from fastapi import APIRouter, FastAPI
from starlette.middleware.cors import CORSMiddleware
import os

from database import client, ensure_indexes
from scoring import SETTINGS
from scheduler import start_scheduler, shutdown_scheduler
from security_middleware import SecurityHeadersMiddleware, RateLimitMiddleware
import routes_auth
import routes_assets
import routes_watchlist
import routes_alerts
import routes_screener
import routes_billing
import routes_admin
import routes_market
import routes_plans
import routes_portfolio
import routes_backtest
import routes_ai
import routes_intel
import routes_catalog

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Optional error tracking: only initializes when SENTRY_DSN is set, so it's a
# no-op in dev and doesn't require any account. Defensive import so a missing
# package can never block startup.
_sentry_dsn = os.environ.get("SENTRY_DSN")
if _sentry_dsn:
    try:
        import sentry_sdk
        sentry_sdk.init(
            dsn=_sentry_dsn,
            environment=os.environ.get("ENV", "development"),
            traces_sample_rate=0.0,  # errors only, no perf tracing (no cost surprise)
            send_default_pii=False,
        )
        logger.info("Sentry error tracking enabled.")
    except Exception as e:  # noqa: BLE001
        logger.warning("Sentry init failed (continuing without it): %s", e)

app = FastAPI(title="Dipzee API")

api_router = APIRouter(prefix="/api")


@api_router.get("/")
async def root():
    return {"message": "Dipzee API", "status": "ok"}


@api_router.get("/health")
async def health():
    """Unauthenticated readiness probe for the load balancer / uptime monitor
    and the CI post-deploy check. Unlike ``/`` (a static "ok"), this actually
    verifies the DB responds and the background scheduler is running, and
    returns 503 if either is down — so a process that booted but is broken
    (Mongo unreachable, scheduler failed to start) is reported unhealthy
    instead of silently serving a green light.
    """
    from fastapi.responses import JSONResponse
    from database import db as _db
    from scheduler import is_scheduler_running

    checks = {"db": False, "scheduler": is_scheduler_running()}
    try:
        await _db.command("ping")
        checks["db"] = True
    except Exception as e:  # noqa: BLE001
        logger.error("[health] DB ping failed: %s", e)

    ok = checks["db"] and checks["scheduler"]
    # `commit` is the git SHA baked into the image at build time (GIT_SHA
    # build-arg, set by CI to github.sha). It answers "exactly which revision
    # is live right now?" — so a deploy can be verified in one call instead of
    # guessing. "dev" locally / when unstamped.
    body = {"status": "ok" if ok else "degraded", "checks": checks, "commit": os.environ.get("GIT_SHA", "dev")}
    return JSONResponse(body, status_code=200 if ok else 503)


@api_router.get("/settings/scoring")
async def scoring_settings():
    """Expose the configurable scoring weights/thresholds (transparency)."""
    return SETTINGS


# Mount feature routers under /api
api_router.include_router(routes_auth.router)
api_router.include_router(routes_assets.router)
api_router.include_router(routes_watchlist.router)
api_router.include_router(routes_alerts.router)
api_router.include_router(routes_screener.router)
api_router.include_router(routes_billing.router)
api_router.include_router(routes_admin.router)
api_router.include_router(routes_market.router)
api_router.include_router(routes_plans.router)
api_router.include_router(routes_portfolio.router)
api_router.include_router(routes_backtest.router)
api_router.include_router(routes_ai.router)
api_router.include_router(routes_intel.router)
api_router.include_router(routes_catalog.router)

app.include_router(api_router)

# Security middleware. Added before CORS so that CORS remains the OUTERMOST
# layer (it must decorate even 429/limited responses with the right headers).
app.add_middleware(RateLimitMiddleware)
app.add_middleware(SecurityHeadersMiddleware)

ENV = os.environ.get("ENV", "development")
_cors_raw = os.environ.get("CORS_ORIGINS")
if _cors_raw:
    _cors_origins = [o.strip() for o in _cors_raw.split(",") if o.strip()]
elif ENV == "production":
    logger.error("CORS_ORIGINS not set in production — denying all cross-origin requests.")
    _cors_origins = []
else:
    _cors_origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=_cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def on_startup():
    from app_config import validate_production_config
    validate_production_config()
    # Normalize data before creating constraints. Both operations fail
    # startup: auth/payment traffic must never run without their invariants.
    from database import db as _db
    from migrations.runner import run_pending_migrations
    await run_pending_migrations(_db)
    await ensure_indexes()
    logger.info("Indexes ensured.")

    try:
        await seed_superadmin()
    except Exception as e:  # noqa: BLE001
        logger.warning("seed_superadmin failed: %s", e)
    try:
        await routes_admin.load_scoring_settings()
    except Exception as e:  # noqa: BLE001
        logger.warning("load_scoring_settings failed: %s", e)
    try:
        # Seed the knowledge graph if empty (idempotent, cheap). Best-effort:
        # a failure here must never block startup — the graph rebuilds lazily.
        from knowledge_graph import load_graph
        from database import db as _kgdb
        await load_graph(_kgdb)
    except Exception as e:  # noqa: BLE001
        logger.warning("knowledge graph seed failed: %s", e)
    try:
        # Seed the security-master catalog (US listed universe) if empty, so a
        # fresh deploy can browse Markets → Explore without a manual admin
        # import. Best-effort: fetches the public Nasdaq Trader directory; a
        # network failure just leaves it empty until the admin/scheduler import.
        from database import db as _catdb
        if await _catdb.security_master.count_documents({}) == 0:
            import security_master
            await security_master.import_us_listings(fetch=True)
    except Exception as e:  # noqa: BLE001
        logger.warning("security-master seed failed: %s", e)
    try:
        # Mark verified dividend yields on catalog rows from the scored assets
        # (real data only; grows as more names get refreshed). Best-effort.
        import security_master
        await security_master.enrich_dividends_from_assets()
    except Exception as e:  # noqa: BLE001
        logger.warning("dividend enrich failed: %s", e)
    try:
        start_scheduler()
    except Exception as e:  # noqa: BLE001
        # Logged at ERROR (not warning): if the scheduler doesn't start, no
        # background refresh / alert evaluation / billing reconciliation runs.
        # The /api/health readiness probe reports "degraded" (scheduler=false)
        # so this surfaces to the uptime monitor instead of booting green.
        logger.error("scheduler start failed — background jobs are NOT running: %s", e)


async def seed_superadmin():
    """Create/upgrade the configured superadmin account(s) (idempotent).

    Superadmin emails/password come exclusively from SUPERADMIN_EMAIL
    (comma-separated) and SUPERADMIN_PASSWORD. If either is unset, no account
    is created or modified — there is no built-in credential fallback.
    """
    import os
    import uuid
    from datetime import datetime, timezone
    from database import db
    from security import hash_password

    raw = os.environ.get("SUPERADMIN_EMAIL") or ""
    emails = list(dict.fromkeys(e.strip().lower() for e in raw.split(",") if e.strip()))
    password = os.environ.get("SUPERADMIN_PASSWORD") or ""
    if not emails or not password:
        logger.warning("SUPERADMIN_EMAIL/SUPERADMIN_PASSWORD not set — skipping superadmin seed.")
        return
    for email in emails:
        existing = await db.users.find_one({"email": email})
        if existing:
            await db.users.update_one(
                {"email": email},
                # Preserve password rotations performed through the product;
                # a long-lived environment secret must not reset credentials
                # on every container restart.
                {"$set": {"role": "superadmin", "plan": "investor"}},
            )
            logger.info("Superadmin ensured: %s", email)
            continue
        await db.users.insert_one({
            "id": str(uuid.uuid4()),
            "email": email,
            "hashed_password": hash_password(password),
            "display_name": email.split("@")[0],
            "bio": "",
            "avatar": None,
            "phone": "",
            "country": "",
            "telegram_chat_id": "",
            "webhook_url": "",
            "locale": "en",
            "currency": "USD",
            "plan": "investor",
            "role": "superadmin",
            "auth_version": 0,
            "stripe_customer_id": None,
            "default_alert_prefs": {"email": True, "in_app": True, "telegram": False, "webhook": False},
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        logger.info("Superadmin created: %s", email)


@app.on_event("shutdown")
async def shutdown_db_client():
    shutdown_scheduler()
    client.close()
