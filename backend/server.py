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
        start_scheduler()
    except Exception as e:  # noqa: BLE001
        logger.warning("scheduler start failed: %s", e)


@app.on_event("shutdown")
async def shutdown_db_client():
    shutdown_scheduler()
    client.close()
