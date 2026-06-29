"""Alert evaluation engine with edge-triggering.

Fires an alert once when its condition becomes true (transition from false->true),
not repeatedly. State is tracked via the alert's last_triggered_at plus the
asset's previous values (prev_price/prev_score/prev_flags) stored on refresh.
"""
import logging
import uuid
from datetime import datetime, timezone

from database import db
from explain import build_alert_message
from email_service import send_email

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _condition_met(alert: dict, asset: dict):
    """Return (met: bool, extra_params: dict) for the current asset snapshot."""
    t = alert["type"]
    params = alert.get("params") or {}
    price = asset.get("price")
    flags = asset.get("flags") or {}
    prev_flags = asset.get("prev_flags") or {}
    score = asset.get("score")
    prev_score = asset.get("prev_score")
    prev_price = asset.get("prev_price")
    dy = asset.get("dividend_yield")
    prev_dy = asset.get("prev_dividend_yield")
    target = asset.get("target_mean")

    if t == "buy_zone":
        return (bool(flags.get("buy_zone")) and not prev_flags.get("buy_zone"), {})
    if t == "sell_zone":
        return (bool(flags.get("sell_zone")) and not prev_flags.get("sell_zone"), {})
    if t == "target_reached":
        if price is None or not target:
            return (False, {})
        now_true = price >= target
        prev_true = prev_price is not None and prev_price >= target
        return (now_true and not prev_true, {})
    if t == "price_below":
        v = params.get("value")
        if v is None or price is None:
            return (False, {})
        now_true = price < v
        prev_true = prev_price is not None and prev_price < v
        return (now_true and not prev_true, {})
    if t == "price_above":
        v = params.get("value")
        if v is None or price is None:
            return (False, {})
        now_true = price > v
        prev_true = prev_price is not None and prev_price > v
        return (now_true and not prev_true, {})
    if t == "score_threshold":
        v = params.get("value")
        if v is None or score is None:
            return (False, {})
        now_true = score >= v
        prev_true = prev_score is not None and prev_score >= v
        return (now_true and not prev_true, {})
    if t == "dividend_change":
        if dy is None or prev_dy is None:
            return (False, {})
        # fire on any change > 0.1 percentage point
        return (abs(dy - prev_dy) >= 0.001, {})
    if t == "daily_drop":
        pct = params.get("value", 5) / 100.0
        if price is None or not prev_price:
            return (False, {})
        drop = (price - prev_price) / prev_price
        return (drop <= -pct, {"observed_drop": drop})
    return (False, {})


async def evaluate_alerts_for_asset(asset: dict):
    """Evaluate all active alerts on this asset's ticker and fire events."""
    if not asset:
        return
    ticker = asset.get("ticker")
    alerts = await db.alerts.find({"ticker": ticker, "active": True}).to_list(1000)
    for alert in alerts:
        try:
            met, extra = _condition_met(alert, asset)
            if not met:
                continue
            user = await db.users.find_one({"id": alert["user_id"]})
            locale = (user or {}).get("locale", "en")
            params = dict(alert.get("params") or {})
            params.update(extra)
            message = build_alert_message(alert["type"], asset, params, locale)
            event = {
                "id": str(uuid.uuid4()),
                "user_id": alert["user_id"],
                "alert_id": alert["id"],
                "ticker": ticker,
                "type": alert["type"],
                "message": message,
                "payload": {
                    "price": asset.get("price"),
                    "score": asset.get("score"),
                    "classification": asset.get("classification"),
                    "currency": asset.get("currency"),
                },
                "read": False,
                "created_at": _now_iso(),
            }
            await db.alert_events.insert_one(event)
            await db.alerts.update_one({"id": alert["id"]}, {"$set": {"last_triggered_at": _now_iso()}})

            prefs = (user or {}).get("default_alert_prefs", {}) or {}
            if prefs.get("email", True) and user and user.get("email"):
                subject = f"Dipzee \u2022 {ticker}: {alert['type'].replace('_', ' ').title()}"
                html = f"<div style='font-family:Inter,Arial,sans-serif'><h2 style='color:#1A1F4D'>Dipzee</h2><p>{message}</p><p style='color:#5B6478;font-size:12px'>Educational information, not financial advice.</p></div>"
                send_email(user["email"], subject, html)
        except Exception as e:  # noqa: BLE001
            logger.warning("Alert evaluation failed for alert %s: %s", alert.get("id"), e)
