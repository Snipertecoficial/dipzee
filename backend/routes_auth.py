"""Auth routes: register, login, current user, profile/settings update."""
import asyncio
import base64
import hashlib
import logging
import re
import secrets
import uuid
from datetime import datetime, timezone, timedelta
from io import BytesIO
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from PIL import Image
from pydantic import BaseModel, EmailStr, Field

from database import db
from email_service import send_email
import login_guard
import refresh_tokens
from routes_billing import cancel_subscription_silently
from security import (
    create_access_token,
    get_current_user,
    hash_password,
    serialize_user,
    verify_password,
)
from url_safety import assert_safe_outbound_url, UnsafeUrlError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])

RESET_TOKEN_TTL_MINUTES = 60
# Bump when the Terms/Privacy Policy content materially changes; stored on
# each user so we always know which version they agreed to.
TERMS_VERSION = "2026-07-17"

# A real bcrypt hash of a fixed, unusable value — verified against on every
# login attempt for an email that doesn't exist, so that branch costs the
# same bcrypt-bound time as a real "wrong password" check. Without this, an
# unknown email short-circuits before hashing and returns measurably faster
# than a registered one, letting an attacker enumerate valid emails purely
# from response timing even though the response body is identical either way.
_DUMMY_PASSWORD_HASH = "$2b$12$bM/C6MCqR3O.cZ/M1/jce.zXlR89UBV51096/.ejQXS1dypndp2oy"

VALID_CURRENCIES = {"CAD", "USD", "BRL"}
VALID_LOCALES = {"en", "fr", "pt", "es"}

# Strip control characters from free-text profile fields (defense-in-depth
# against stored-XSS / log injection; React already escapes on render).
_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def _sanitize_text(v: Optional[str]) -> str:
    return _CONTROL_RE.sub("", v or "").strip()


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    locale: str = "en"
    currency: str = "USD"
    consent_accepted: bool = False


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class ForgotIn(BaseModel):
    email: EmailStr
    origin_url: str


class ResetIn(BaseModel):
    token: str
    password: str = Field(min_length=6)


class RefreshIn(BaseModel):
    refresh_token: str


class LogoutIn(BaseModel):
    refresh_token: str


class ChangePasswordIn(BaseModel):
    current_password: str
    new_password: str = Field(min_length=6)


class ProfileIn(BaseModel):
    locale: Optional[str] = None
    currency: Optional[str] = None
    default_alert_prefs: Optional[dict] = None
    display_name: Optional[str] = Field(default=None, max_length=80)
    bio: Optional[str] = Field(default=None, max_length=280)
    phone: Optional[str] = Field(default=None, max_length=30)
    country: Optional[str] = Field(default=None, max_length=60)
    avatar: Optional[str] = None  # base64 data URL (size-limited below)
    telegram_chat_id: Optional[str] = Field(default=None, max_length=40)
    webhook_url: Optional[str] = Field(default=None, max_length=400)


MAX_AVATAR_CHARS = 2_000_000  # ~1.4MB image encoded as base64
MAX_AVATAR_BYTES = 1_500_000  # decoded
ALLOWED_AVATAR_FORMATS = {"PNG", "JPEG", "WEBP", "GIF"}


def _validate_avatar(data_url: str) -> None:
    """Reject anything that isn't a genuine, decodable raster image.

    A bare ``startswith("data:image/")`` check (the old validation) accepts
    any string with that prefix, including non-base64 payloads or formats
    like SVG that can carry embedded scripts — decoding and asking Pillow to
    parse the actual bytes closes that gap instead of trusting the label.
    """
    header, _, encoded = data_url.partition(",")
    if ";base64" not in header:
        raise HTTPException(status_code=400, detail="Avatar must be a base64-encoded image data URL")
    try:
        raw = base64.b64decode(encoded, validate=True)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid base64 image data")
    if len(raw) > MAX_AVATAR_BYTES:
        raise HTTPException(status_code=413, detail={"code": "avatar_too_large", "message": "Image too large (max ~1.4MB)."})
    try:
        img = Image.open(BytesIO(raw))
        img_format = img.format
        img.verify()
    except Exception:
        raise HTTPException(status_code=400, detail="File is not a valid image")
    if img_format not in ALLOWED_AVATAR_FORMATS:
        raise HTTPException(status_code=400, detail=f"Unsupported image format: {img_format}")


async def _auth_response(user: dict) -> dict:
    token = create_access_token(user["id"])
    refresh_token = await refresh_tokens.issue(user["id"])
    return {
        "access_token": token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": serialize_user(user),
    }


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _welcome_email_html(display_name: str) -> str:
    return (
        f"<h2>Bem-vindo ao Dipzee, {display_name}!</h2>"
        "<p>Sua conta foi criada com sucesso. Boas análises e bons investimentos!</p>"
    )


def _reset_email_html(link: str) -> str:
    return (
        "<h2>Redefinir senha — Dipzee</h2>"
        f"<p>Clique no link abaixo para criar uma nova senha. Ele expira em {RESET_TOKEN_TTL_MINUTES} minutos.</p>"
        f'<p><a href="{link}">{link}</a></p>'
        "<p>Se você não pediu essa alteração, pode ignorar este e-mail com segurança.</p>"
    )


@router.post("/register")
async def register(body: RegisterIn):
    if not body.consent_accepted:
        raise HTTPException(status_code=400, detail="You must accept the Terms of Service and Privacy Policy")
    email = body.email.lower()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=400, detail="Email already registered")
    locale = body.locale if body.locale in VALID_LOCALES else "en"
    currency = body.currency if body.currency in VALID_CURRENCIES else "USD"
    now_iso = datetime.now(timezone.utc).isoformat()
    user = {
        "id": str(uuid.uuid4()),
        "email": email,
        "hashed_password": hash_password(body.password),
        "display_name": email.split("@")[0],
        "bio": "",
        "avatar": None,
        "phone": "",
        "country": "",
        "telegram_chat_id": "",
        "webhook_url": "",
        "locale": locale,
        "currency": currency,
        "plan": "none",
        "role": "user",
        "stripe_customer_id": None,
        "default_alert_prefs": {"email": True, "in_app": True, "telegram": False, "webhook": False},
        "consent_accepted_at": now_iso,
        "terms_version": TERMS_VERSION,
        "created_at": now_iso,
    }
    await db.users.insert_one(user)
    try:
        await asyncio.to_thread(send_email, email, "Bem-vindo ao Dipzee", _welcome_email_html(user["display_name"]))
    except Exception as e:  # noqa: BLE001
        logger.warning("welcome email failed for %s: %s", email, e)
    return await _auth_response(user)


@router.post("/forgot")
async def forgot_password(body: ForgotIn):
    """Always responds the same way regardless of whether the email exists."""
    email = body.email.lower()
    user = await db.users.find_one({"email": email})
    if user:
        raw_token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=RESET_TOKEN_TTL_MINUTES)
        await db.password_resets.update_one(
            {"user_id": user["id"]},
            {"$set": {
                "token_hash": _hash_token(raw_token),
                "expires_at": expires_at.isoformat(),
                "used": False,
            }},
            upsert=True,
        )
        link = f"{body.origin_url.rstrip('/')}/reset-password?token={raw_token}"
        try:
            await asyncio.to_thread(send_email, email, "Redefinir sua senha — Dipzee", _reset_email_html(link))
        except Exception as e:  # noqa: BLE001
            logger.warning("reset email failed for %s: %s", email, e)
    return {"message": "If that email exists, a password reset link has been sent."}


@router.post("/reset")
async def reset_password(body: ResetIn):
    doc = await db.password_resets.find_one({"token_hash": _hash_token(body.token), "used": False})
    if not doc:
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    expires_at = datetime.fromisoformat(doc["expires_at"])
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) > expires_at:
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    await db.users.update_one({"id": doc["user_id"]}, {"$set": {"hashed_password": hash_password(body.password)}})
    await db.password_resets.update_one({"_id": doc["_id"]}, {"$set": {"used": True}})
    # Anyone who could reset the password could also have been the reason it
    # needed resetting — kill every existing session rather than leaving old
    # ones (possibly the attacker's) valid.
    await refresh_tokens.revoke_all(doc["user_id"])
    return {"message": "Password updated"}


@router.post("/login")
async def login(body: LoginIn):
    email = body.email.lower()
    locked, remaining = await login_guard.check_locked(email)
    if locked:
        mins = max(remaining // 60, 1)
        raise HTTPException(
            status_code=429,
            detail=f"Conta temporariamente bloqueada por tentativas excessivas. Tente novamente em ~{mins} min.",
        )
    user = await db.users.find_one({"email": email})
    # Always run the bcrypt comparison, even for an unknown email (against a
    # dummy hash) — `or` would otherwise short-circuit and skip it, making
    # this branch measurably faster than a real "wrong password" and
    # leaking which emails are registered via response timing.
    password_ok = verify_password(body.password, (user or {}).get("hashed_password", _DUMMY_PASSWORD_HASH))
    if not user or not password_ok:
        await login_guard.record_failure(email)
        raise HTTPException(status_code=401, detail="Invalid email or password")
    await login_guard.record_success(email)
    return await _auth_response(user)


@router.post("/refresh")
async def refresh(body: RefreshIn):
    """Exchange a refresh token for a new short-lived access token.

    The refresh token itself is rotated (old one revoked, new one issued) so
    a leaked-and-later-replayed token is detectable — see refresh_tokens.py.
    """
    result = await refresh_tokens.rotate(body.refresh_token)
    if not result:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
    user_id, new_refresh_token = result
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return {
        "access_token": create_access_token(user_id),
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
    }


@router.post("/logout")
async def logout(body: LogoutIn):
    """Revoke a single refresh token (this device/session). Always 200."""
    await refresh_tokens.revoke(body.refresh_token)
    return {"ok": True}


@router.post("/logout-all")
async def logout_all(user: dict = Depends(get_current_user)):
    """Revoke every refresh token for the current user ('sign out everywhere')."""
    await refresh_tokens.revoke_all(user["id"])
    return {"ok": True}


@router.post("/change-password")
async def change_password(body: ChangePasswordIn, user: dict = Depends(get_current_user)):
    if not verify_password(body.current_password, user["hashed_password"]):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    await db.users.update_one({"id": user["id"]}, {"$set": {"hashed_password": hash_password(body.new_password)}})
    # Rotate out every other session (possibly an attacker's) while keeping
    # this one alive — the caller just proved they know the new password.
    await refresh_tokens.revoke_all(user["id"])
    new_refresh_token = await refresh_tokens.issue(user["id"])
    return {
        "access_token": create_access_token(user["id"]),
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
    }


@router.get("/me")
async def me(user: dict = Depends(get_current_user)):
    return serialize_user(user)


@router.put("/profile")
async def update_profile(body: ProfileIn, user: dict = Depends(get_current_user)):
    updates = {}
    if body.locale and body.locale in VALID_LOCALES:
        updates["locale"] = body.locale
    if body.currency and body.currency in VALID_CURRENCIES:
        updates["currency"] = body.currency
    if body.default_alert_prefs is not None:
        updates["default_alert_prefs"] = body.default_alert_prefs
    for field in ("display_name", "bio", "phone", "country", "telegram_chat_id"):
        val = getattr(body, field)
        if val is not None:
            updates[field] = _sanitize_text(val)
    if body.webhook_url is not None:
        wh = _sanitize_text(body.webhook_url)
        if wh:
            try:
                assert_safe_outbound_url(wh)
            except UnsafeUrlError as e:
                raise HTTPException(status_code=400, detail=str(e))
        updates["webhook_url"] = wh
    if body.avatar is not None:
        av = body.avatar.strip()
        if av:
            if len(av) > MAX_AVATAR_CHARS:
                raise HTTPException(status_code=413, detail={"code": "avatar_too_large", "message": "Image too large (max ~1.4MB)."})
            _validate_avatar(av)
        updates["avatar"] = av or None
    if updates:
        await db.users.update_one({"id": user["id"]}, {"$set": updates})
    fresh = await db.users.find_one({"id": user["id"]})
    return serialize_user(fresh)


@router.get("/me/export")
async def export_my_data(user: dict = Depends(get_current_user)):
    """Everything Dipzee holds about this account, as one JSON document.

    Covers the data-portability/right-of-access obligations shared by LGPD
    (Art. 18), GDPR (Art. 15/20), PIPEDA and CCPA/CPRA.
    """
    uid = user["id"]
    profile = await db.users.find_one({"id": uid}, {"_id": 0, "hashed_password": 0})
    watchlist = await db.watchlist_items.find({"user_id": uid}, {"_id": 0}).to_list(2000)
    alerts = await db.alerts.find({"user_id": uid}, {"_id": 0}).to_list(2000)
    alert_events = await db.alert_events.find({"user_id": uid}, {"_id": 0}).to_list(2000)
    positions = await db.positions.find({"user_id": uid}, {"_id": 0}).to_list(2000)
    transactions = await db.payment_transactions.find({"user_id": uid}, {"_id": 0}).to_list(2000)
    return {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "profile": profile,
        "watchlist": watchlist,
        "alerts": alerts,
        "alert_events": alert_events,
        "portfolio_positions": positions,
        "payment_transactions": transactions,
    }


@router.delete("/me")
async def delete_my_account(user: dict = Depends(get_current_user)):
    """Self-service account deletion (right to erasure / eliminação).

    Superadmin accounts are excluded — deleting your own admin access would
    be irreversible from inside the same session; another admin (or direct
    DB access) has to do it instead. Billing/payment records are kept for
    accounting and tax retention even though the account itself is erased;
    only the live subscription is canceled so nothing bills again.
    """
    if user.get("role") == "superadmin":
        raise HTTPException(status_code=400, detail="Superadmin accounts can't be self-deleted. Ask another admin to remove your access.")
    uid = user["id"]
    await cancel_subscription_silently(user.get("stripe_subscription_id"))
    await db.watchlist_items.delete_many({"user_id": uid})
    await db.alerts.delete_many({"user_id": uid})
    await db.alert_events.delete_many({"user_id": uid})
    await db.positions.delete_many({"user_id": uid})
    await db.password_resets.delete_many({"user_id": uid})
    await db.refresh_tokens.delete_many({"user_id": uid})
    await db.users.delete_one({"id": uid})
    return {"ok": True}
