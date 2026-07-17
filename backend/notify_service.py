"""Multi-channel alert delivery.

Channels:
- in-app: handled by alert_service (event stored in DB).
- email: always attempted when the user opts in (currently via email_service,
  which logs unless a real provider key is configured).
- telegram: works out of the box once TELEGRAM_BOT_TOKEN is set (free bot) and
  the user saved their chat id. Gated to plans with `messaging_alerts` (Investor).
- webhook: user-provided URL (works now, no keys). Great for Slack/Discord/Zapier
  which can forward to WhatsApp/Telegram. Gated to `messaging_alerts` (Investor).
"""
import asyncio
import logging
import os

import requests

from email_service import send_email
from plans import has_feature
from url_safety import assert_safe_outbound_url

logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")


def _send_telegram(chat_id: str, text: str):
    if not TELEGRAM_TOKEN:
        return
    requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
        json={"chat_id": chat_id, "text": text, "disable_web_page_preview": False},
        timeout=8,
    )


def _send_webhook(url: str, payload: dict):
    # Re-checked here, not just at save time in routes_auth.py: a hostname
    # can resolve to a public IP when the user saves it and to an internal
    # one later (DNS rebinding), and a "safe" URL can 302 to an internal one
    # — hence also disabling redirects rather than following them blindly.
    assert_safe_outbound_url(url)
    requests.post(url, json=payload, timeout=8, allow_redirects=False)


async def deliver(user: dict, *, ticker: str, event_type: str, message: str,
                  subject: str, html: str, url: str = None):
    """Fan out an alert to all channels the user enabled and their plan allows."""
    if not user:
        return
    prefs = user.get("default_alert_prefs", {}) or {}
    plan = user.get("plan")

    if prefs.get("email", True) and user.get("email"):
        try:
            await asyncio.to_thread(send_email, user["email"], subject, html)
        except Exception as e:  # noqa: BLE001
            logger.warning("email delivery failed: %s", e)

    if has_feature(plan, "messaging_alerts"):
        if prefs.get("telegram") and user.get("telegram_chat_id") and TELEGRAM_TOKEN:
            try:
                await asyncio.to_thread(_send_telegram, user["telegram_chat_id"], f"\U0001F4C8 Dipzee \u2022 {ticker}\n{message}")
            except Exception as e:  # noqa: BLE001
                logger.warning("telegram delivery failed: %s", e)
        if prefs.get("webhook") and user.get("webhook_url"):
            payload = {"service": "dipzee", "ticker": ticker, "type": event_type, "message": message, "url": url}
            try:
                await asyncio.to_thread(_send_webhook, user["webhook_url"], payload)
            except Exception as e:  # noqa: BLE001
                logger.warning("webhook delivery failed: %s", e)
