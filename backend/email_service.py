"""Resend email wrapper. No-ops gracefully when RESEND_API_KEY is not set.

Replace nothing here when keys arrive; just set RESEND_API_KEY in .env.
"""
import logging
import os

import requests

logger = logging.getLogger(__name__)

RESEND_URL = "https://api.resend.com/emails"


def is_configured() -> bool:
    return bool(os.environ.get("RESEND_API_KEY"))


def send_email(to: str, subject: str, html: str) -> bool:
    api_key = os.environ.get("RESEND_API_KEY")
    sender = os.environ.get("RESEND_FROM_EMAIL", "Dipzee <onboarding@resend.dev>")
    if not api_key:
        logger.info("[email_service] RESEND_API_KEY not set; skipping email to %s (%s)", to, subject)
        return False
    try:
        resp = requests.post(
            RESEND_URL,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"from": sender, "to": [to], "subject": subject, "html": html},
            timeout=15,
        )
        if resp.status_code >= 400:
            logger.warning("[email_service] Resend error %s: %s", resp.status_code, resp.text)
            return False
        return True
    except Exception as e:  # noqa: BLE001
        logger.warning("[email_service] Failed to send email: %s", e)
        return False
