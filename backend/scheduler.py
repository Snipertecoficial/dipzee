"""APScheduler jobs for Dipzee.

- Daily job: refresh all monitored tickers after the North-American market close.
- Intraday job: every 15 minutes during market hours, refresh monitored tickers
  that belong to at least one Investor-plan user (intraday is an Investor feature).

A "monitored" ticker is any ticker present in a watchlist item or an active alert.
Alert rules are evaluated on every refresh (edge-triggered inside alert_service).
"""
import logging
from datetime import datetime

import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from database import db
from asset_service import refresh_asset
from alert_service import evaluate_alerts_for_asset, evaluate_news_alerts

logger = logging.getLogger(__name__)
ET = pytz.timezone("America/New_York")

_scheduler: AsyncIOScheduler | None = None


async def _monitored_tickers() -> set:
    tickers = set()
    async for item in db.watchlist_items.find({}, {"ticker": 1}):
        if item.get("ticker"):
            tickers.add(item["ticker"])
    async for alert in db.alerts.find({"active": True}, {"ticker": 1}):
        if alert.get("ticker"):
            tickers.add(alert["ticker"])
    return tickers


async def _intraday_tickers() -> set:
    """Tickers monitored by at least one Investor-plan user."""
    investor_ids = [u["id"] async for u in db.users.find({"plan": "investor"}, {"id": 1})]
    if not investor_ids:
        return set()
    tickers = set()
    async for item in db.watchlist_items.find({"user_id": {"$in": investor_ids}}, {"ticker": 1}):
        tickers.add(item["ticker"])
    async for alert in db.alerts.find({"user_id": {"$in": investor_ids}, "active": True}, {"ticker": 1}):
        tickers.add(alert["ticker"])
    return tickers


def _is_market_hours() -> bool:
    now = datetime.now(ET)
    if now.weekday() >= 5:  # Sat/Sun
        return False
    minutes = now.hour * 60 + now.minute
    return (9 * 60 + 30) <= minutes <= (16 * 60)


async def _refresh_set(tickers: set, label: str, force_target: bool = False):
    if not tickers:
        return
    logger.info("[scheduler] %s refreshing %d tickers", label, len(tickers))
    for tk in tickers:
        try:
            asset = await refresh_asset(tk, force_target=force_target)
            if asset:
                await evaluate_alerts_for_asset(asset)
        except Exception as e:  # noqa: BLE001
            logger.warning("[scheduler] refresh failed for %s: %s", tk, e)


async def daily_refresh_job():
    tickers = await _monitored_tickers()
    # Also keep the screener universe fresh for the daily batch.
    try:
        from screener_service import UNIVERSE
        tickers = tickers.union(set(UNIVERSE))
    except Exception:  # noqa: BLE001
        pass
    await _refresh_set(tickers, "daily", force_target=True)
    await evaluate_news_alerts()


async def intraday_refresh_job():
    if not _is_market_hours():
        return
    tickers = await _intraday_tickers()
    await _refresh_set(tickers, "intraday")


async def news_job():
    try:
        await evaluate_news_alerts()
    except Exception as e:  # noqa: BLE001
        logger.warning("[scheduler] news job failed: %s", e)


async def billing_sync_job():
    """Catch payments the app's own redirect-back polling and the webhook
    both missed (closed tab, misconfigured/unregistered webhook, etc.) so a
    transaction never sits stuck showing "initiated" after the customer
    actually paid — see routes_billing.reconcile_pending_transactions."""
    try:
        from routes_billing import reconcile_pending_transactions
        result = await reconcile_pending_transactions()
        if result.get("updated"):
            logger.info("[scheduler] billing sync: %d/%d transactions updated", result["updated"], result["checked"])
    except Exception as e:  # noqa: BLE001
        logger.warning("[scheduler] billing sync job failed: %s", e)


def start_scheduler():
    global _scheduler
    if _scheduler is not None:
        return _scheduler
    _scheduler = AsyncIOScheduler(timezone=ET)
    # Daily after NA market close (16:15 ET) on weekdays
    _scheduler.add_job(daily_refresh_job, CronTrigger(day_of_week="mon-fri", hour=16, minute=15, timezone=ET), id="daily_refresh", replace_existing=True)
    # Intraday every 15 minutes (the job itself checks market hours + investor users)
    _scheduler.add_job(intraday_refresh_job, IntervalTrigger(minutes=15), id="intraday_refresh", replace_existing=True)
    # News monitoring every 20 minutes
    _scheduler.add_job(news_job, IntervalTrigger(minutes=20), id="news_job", replace_existing=True)
    # Billing reconciliation every 10 minutes
    _scheduler.add_job(billing_sync_job, IntervalTrigger(minutes=10), id="billing_sync_job", replace_existing=True)
    _scheduler.start()
    logger.info("[scheduler] started (daily 16:15 ET + intraday 15min + news 20min + billing sync 10min)")
    return _scheduler


def shutdown_scheduler():
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None


def is_scheduler_running() -> bool:
    """Return True if the background scheduler is initialized and running."""
    return bool(_scheduler and _scheduler.running)
