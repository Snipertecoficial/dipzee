"""Resend email wrapper. No-ops gracefully when RESEND_API_KEY is not set.

Replace nothing here when keys arrive; just set RESEND_API_KEY in .env.
"""
import logging
import os

import requests

logger = logging.getLogger(__name__)

RESEND_URL = "https://api.resend.com/emails"

# The .env.example placeholder. A key equal to this is "present" (truthy) but
# will 4xx on every send, so it must NOT count as configured.
_PLACEHOLDER_KEYS = {"", "re_...", "re_your_key_here"}


def is_configured() -> bool:
    return bool(os.environ.get("RESEND_API_KEY"))


def is_really_configured() -> bool:
    """True only when a plausibly-real Resend key is set (not empty, not the
    documented placeholder). Used by the admin health panel so a placeholder
    key doesn't show a green light while every send silently 4xx's."""
    key = (os.environ.get("RESEND_API_KEY") or "").strip()
    return bool(key) and key not in _PLACEHOLDER_KEYS and key.startswith("re_") and len(key) > 12


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
            # A configured key that still fails is a real delivery failure, not
            # a benign "not set up yet" — log at ERROR so it's visible.
            logger.error("[email_service] Resend error %s sending to %s: %s", resp.status_code, to, resp.text)
            return False
        return True
    except Exception as e:  # noqa: BLE001
        logger.error("[email_service] Failed to send email to %s: %s", to, e)
        return False
