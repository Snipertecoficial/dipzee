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
from notify_service import deliver

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
        if alert.get("type") == "news":
            continue  # handled by evaluate_news_alerts
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
            if user:
                subject = f"Dipzee \u2022 {ticker}: {alert['type'].replace('_', ' ').title()}"
                html = f"<div style='font-family:Inter,Arial,sans-serif'><h2 style='color:#1A1F4D'>Dipzee</h2><p>{message}</p><p style='color:#5B6478;font-size:12px'>Educational information, not financial advice.</p></div>"
                await deliver(user, ticker=ticker, event_type=alert["type"], message=message, subject=subject, html=html)
        except Exception as e:  # noqa: BLE001
            logger.warning("Alert evaluation failed for alert %s: %s", alert.get("id"), e)



NEWS_PREFIX = {
    "en": "News on {ticker}: ",
    "fr": "Actualit\u00e9 sur {ticker} : ",
    "pt": "Not\u00edcia sobre {ticker}: ",
    "es": "Noticia sobre {ticker}: ",
}


async def evaluate_news_alerts():
    """Fire news alerts when company news newer than the alert's checkpoint appears."""
    from providers import get_company_news

    alerts = await db.alerts.find({"type": "news", "active": True}).to_list(1000)
    # group by ticker to minimize API calls
    by_ticker: dict = {}
    for a in alerts:
        by_ticker.setdefault(a["ticker"], []).append(a)

    for ticker, ticker_alerts in by_ticker.items():
        try:
            news = get_company_news(ticker, days=3, limit=20)
        except Exception:  # noqa: BLE001
            news = []
        if not news:
            continue
        for alert in ticker_alerts:
            params = alert.get("params") or {}
            since = params.get("since", 0)
            fresh = [n for n in news if (n.get("datetime") or 0) > since]
            if not fresh:
                continue
            fresh.sort(key=lambda n: n.get("datetime") or 0)
            user = await db.users.find_one({"id": alert["user_id"]})
            locale = (user or {}).get("locale", "en")
            prefix = NEWS_PREFIX.get(locale, NEWS_PREFIX["en"]).format(ticker=ticker)
            newest_ts = since
            for n in fresh:
                newest_ts = max(newest_ts, n.get("datetime") or 0)
                event = {
                    "id": str(uuid.uuid4()),
                    "user_id": alert["user_id"],
                    "alert_id": alert["id"],
                    "ticker": ticker,
                    "type": "news",
                    "message": prefix + (n.get("headline") or ""),
                    "payload": {"url": n.get("url"), "source": n.get("source"), "datetime": n.get("datetime")},
                    "read": False,
                    "created_at": _now_iso(),
                }
                await db.alert_events.insert_one(event)
                if user:
                    html = f"<div style='font-family:Inter,Arial,sans-serif'><h2 style='color:#1A1F4D'>Dipzee</h2><p>{event['message']}</p><p><a href='{n.get('url')}'>{n.get('source')}</a></p></div>"
                    await deliver(user, ticker=ticker, event_type="news", message=event["message"], subject=f"Dipzee \u2022 {ticker} news", html=html, url=n.get("url"))
            # advance checkpoint so each article fires once (edge-triggered)
            await db.alerts.update_one({"id": alert["id"]}, {"$set": {"params.since": newest_ts, "last_triggered_at": _now_iso()}})
