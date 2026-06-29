"""Dipzee FastAPI application entrypoint."""
import logging

from fastapi import APIRouter, FastAPI
from starlette.middleware.cors import CORSMiddleware
import os

from database import client, ensure_indexes
from scoring import SETTINGS
from scheduler import start_scheduler, shutdown_scheduler, daily_refresh_job
import routes_auth
import routes_assets
import routes_watchlist
import routes_alerts
import routes_screener
import routes_billing

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="Dipzee API")

api_router = APIRouter(prefix="/api")


@api_router.get("/")
async def root():
    return {"message": "Dipzee API", "status": "ok"}


@api_router.get("/settings/scoring")
async def scoring_settings():
    """Expose the configurable scoring weights/thresholds (transparency)."""
    return SETTINGS


@api_router.post("/admin/run-daily-refresh")
async def run_daily_refresh():
    """Manually trigger the daily refresh job (useful for testing the scheduler)."""
    await daily_refresh_job()
    return {"ok": True}


# Mount feature routers under /api
api_router.include_router(routes_auth.router)
api_router.include_router(routes_assets.router)
api_router.include_router(routes_watchlist.router)
api_router.include_router(routes_alerts.router)
api_router.include_router(routes_screener.router)
api_router.include_router(routes_billing.router)

app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def on_startup():
    try:
        await ensure_indexes()
        logger.info("Indexes ensured.")
    except Exception as e:  # noqa: BLE001
        logger.warning("ensure_indexes failed: %s", e)
    try:
        await seed_superadmin()
    except Exception as e:  # noqa: BLE001
        logger.warning("seed_superadmin failed: %s", e)
    try:
        start_scheduler()
    except Exception as e:  # noqa: BLE001
        logger.warning("scheduler start failed: %s", e)


async def seed_superadmin():
    """Create/upgrade the configured superadmin account (idempotent)."""
    import os
    import uuid
    from datetime import datetime, timezone
    from database import db
    from security import hash_password

    email = (os.environ.get("SUPERADMIN_EMAIL") or "").lower()
    password = os.environ.get("SUPERADMIN_PASSWORD")
    if not email or not password:
        return
    existing = await db.users.find_one({"email": email})
    if existing:
        await db.users.update_one(
            {"email": email},
            {"$set": {"role": "superadmin", "plan": "investor", "hashed_password": hash_password(password)}},
        )
        logger.info("Superadmin ensured: %s", email)
        return
    await db.users.insert_one({
        "id": str(uuid.uuid4()),
        "email": email,
        "hashed_password": hash_password(password),
        "locale": "pt",
        "currency": "USD",
        "plan": "investor",
        "role": "superadmin",
        "stripe_customer_id": None,
        "default_alert_prefs": {"email": True, "in_app": True},
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    logger.info("Superadmin created: %s", email)


@app.on_event("shutdown")
async def shutdown_db_client():
    shutdown_scheduler()
    client.close()
