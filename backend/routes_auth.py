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
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from PIL import Image
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from pymongo import ReturnDocument

from database import db
from app_config import public_app_url
from email_service import send_email
from email_templates import welcome_email, reset_email
import login_guard
import refresh_tokens
from password_policy import validate_password_strength
from routes_billing import cancel_subscription_for_deletion
from account_service import erase_account_data, export_account_data
from mfa import generate_secret, provisioning_uri, verify_totp
from secret_store import decrypt_secret, encrypt_secret
from security import (
    create_access_token,
    get_current_user,
    hash_password,
    password_needs_rehash,
    serialize_user,
    verify_password,
)
from url_safety import assert_safe_outbound_url, UnsafeUrlError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])

RESET_TOKEN_TTL_MINUTES = 60
REFRESH_COOKIE_NAME = "dz_refresh"
REFRESH_COOKIE_PATH = "/api/auth"
# Server-side password policy (authoritative — the client mirrors it for UX but
# a client can always be bypassed). At least 8 chars, with a letter and a digit.
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
    password: str
    locale: str = "en"
    currency: str = "USD"
    consent_accepted: bool = False

    _pw = field_validator("password")(validate_password_strength)


class LoginIn(BaseModel):
    email: EmailStr
    password: str
    otp: Optional[str] = Field(default=None, pattern=r"^\d{6}$")


class ForgotIn(BaseModel):
    email: EmailStr

    # Older clients sent origin_url. Ignore unknown fields during the rolling
    # deployment, but never use a client-controlled origin for reset links.
    model_config = ConfigDict(extra="ignore")


class ResetIn(BaseModel):
    token: str
    password: str

    _pw = field_validator("password")(validate_password_strength)


class ChangePasswordIn(BaseModel):
    current_password: str
    new_password: str

    _pw = field_validator("new_password")(validate_password_strength)


class MfaEnableIn(BaseModel):
    otp: str = Field(pattern=r"^\d{6}$")


class AlertPreferencesIn(BaseModel):
    email: Optional[bool] = None
    in_app: Optional[bool] = None
    telegram: Optional[bool] = None
    webhook: Optional[bool] = None

    model_config = ConfigDict(extra="forbid")


class ProfileIn(BaseModel):
    locale: Optional[str] = None
    currency: Optional[str] = None
    default_alert_prefs: Optional[AlertPreferencesIn] = None
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


def _set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=token,
        max_age=refresh_tokens.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        path=REFRESH_COOKIE_PATH,
        secure=public_app_url().startswith("https://"),
        httponly=True,
        samesite="strict",
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key=REFRESH_COOKIE_NAME,
        path=REFRESH_COOKIE_PATH,
        secure=public_app_url().startswith("https://"),
        httponly=True,
        samesite="strict",
    )


async def _auth_response(user: dict, response: Response, *, mfa_verified: bool = True) -> dict:
    token = create_access_token(
        user["id"], user.get("auth_version", 0), mfa_verified=mfa_verified,
    )
    refresh_token = await refresh_tokens.issue(user["id"], mfa_verified=mfa_verified)
    _set_refresh_cookie(response, refresh_token)
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": serialize_user(user),
    }


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()




@router.post("/register")
async def register(body: RegisterIn, response: Response):
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
        "auth_version": 0,
        "stripe_customer_id": None,
        "default_alert_prefs": {"email": True, "in_app": True, "telegram": False, "webhook": False},
        "consent_accepted_at": now_iso,
        "terms_version": TERMS_VERSION,
        "created_at": now_iso,
    }
    await db.users.insert_one(user)
    try:
        subject, html = welcome_email(user["display_name"], locale)
        await asyncio.to_thread(send_email, email, subject, html)
    except Exception as e:  # noqa: BLE001
        logger.warning("welcome email failed for %s: %s", email, e)
    return await _auth_response(user, response)


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
                "purge_at": expires_at + timedelta(days=1),
                "used": False,
            }},
            upsert=True,
        )
        link = f"{public_app_url()}/reset-password?token={quote(raw_token, safe='')}"
        subject, html = reset_email(link, RESET_TOKEN_TTL_MINUTES, user.get("locale"))
        sent = await asyncio.to_thread(send_email, email, subject, html)
        if not sent:
            # The user is still told the generic message (no account enumeration),
            # but a failed reset email is a real incident — someone locked out
            # can't recover — so surface it loudly for ops instead of hiding it.
            logger.error("[auth] reset email FAILED to send for %s (RESEND_API_KEY missing/invalid?)", email)
    return {"message": "If that email exists, a password reset link has been sent."}


@router.post("/reset")
async def reset_password(body: ResetIn):
    # Claim the token before changing credentials. A second concurrent request
    # cannot observe/use the same reset token.
    doc = await db.password_resets.find_one_and_update(
        {"token_hash": _hash_token(body.token), "used": False},
        {"$set": {"used": True, "used_at": datetime.now(timezone.utc).isoformat()}},
        return_document=ReturnDocument.BEFORE,
    )
    if not doc:
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    expires_at = datetime.fromisoformat(doc["expires_at"])
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) > expires_at:
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    result = await db.users.update_one(
        {"id": doc["user_id"]},
        {"$set": {"hashed_password": hash_password(body.password)}, "$inc": {"auth_version": 1}},
    )
    if not result.matched_count:
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    # Anyone who could reset the password could also have been the reason it
    # needed resetting — kill every existing session rather than leaving old
    # ones (possibly the attacker's) valid.
    await refresh_tokens.revoke_all(doc["user_id"])
    return {"message": "Password updated"}


@router.post("/login")
async def login(body: LoginIn, response: Response):
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
    if password_needs_rehash(user["hashed_password"]):
        replacement = hash_password(body.password)
        await db.users.update_one(
            {"id": user["id"], "hashed_password": user["hashed_password"]},
            {"$set": {"hashed_password": replacement}},
        )
        user["hashed_password"] = replacement
    mfa_verified = user.get("role") != "superadmin"
    if user.get("role") == "superadmin" and user.get("mfa_enabled"):
        if not body.otp:
            raise HTTPException(
                status_code=401,
                detail={"code": "mfa_required", "message": "Authenticator code required"},
            )
        secret = decrypt_secret(user.get("mfa_secret", ""))
        if not verify_totp(secret, body.otp):
            await login_guard.record_failure(email)
            raise HTTPException(status_code=401, detail="Invalid authenticator code")
        mfa_verified = True
    return await _auth_response(user, response, mfa_verified=mfa_verified)


@router.post("/refresh")
async def refresh(request: Request, response: Response):
    """Exchange a refresh token for a new short-lived access token.

    The refresh token itself is rotated (old one revoked, new one issued) so
    a leaked-and-later-replayed token is detectable — see refresh_tokens.py.
    """
    raw_refresh_token = request.cookies.get(REFRESH_COOKIE_NAME)
    if not raw_refresh_token:
        raise HTTPException(status_code=401, detail="Refresh session missing")
    result = await refresh_tokens.rotate(raw_refresh_token)
    if not result:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
    user_id, new_refresh_token, mfa_verified = result
    user = await db.users.find_one({"id": user_id})
    if not user:
        _clear_refresh_cookie(response)
        raise HTTPException(status_code=401, detail="User not found")
    _set_refresh_cookie(response, new_refresh_token)
    return {
        "access_token": create_access_token(
            user_id, user.get("auth_version", 0), mfa_verified=mfa_verified,
        ),
        "token_type": "bearer",
    }


@router.post("/logout")
async def logout(request: Request, response: Response):
    """Revoke a single refresh token (this device/session). Always 200."""
    raw_refresh_token = request.cookies.get(REFRESH_COOKIE_NAME)
    if raw_refresh_token:
        await refresh_tokens.revoke(raw_refresh_token)
    _clear_refresh_cookie(response)
    return {"ok": True}


@router.post("/logout-all")
async def logout_all(response: Response, user: dict = Depends(get_current_user)):
    """Revoke every refresh token for the current user ('sign out everywhere')."""
    await refresh_tokens.revoke_all(user["id"])
    await db.users.update_one({"id": user["id"]}, {"$inc": {"auth_version": 1}})
    _clear_refresh_cookie(response)
    return {"ok": True}


@router.post("/change-password")
async def change_password(body: ChangePasswordIn, response: Response, user: dict = Depends(get_current_user)):
    if not verify_password(body.current_password, user["hashed_password"]):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    next_version = int(user.get("auth_version", 0)) + 1
    await db.users.update_one(
        {"id": user["id"]},
        {"$set": {"hashed_password": hash_password(body.new_password), "auth_version": next_version}},
    )
    # Rotate out every other session (possibly an attacker's) while keeping
    # this one alive — the caller just proved they know the new password.
    await refresh_tokens.revoke_all(user["id"])
    mfa_verified = bool(user.get("_session_mfa_verified", False))
    new_refresh_token = await refresh_tokens.issue(user["id"], mfa_verified=mfa_verified)
    _set_refresh_cookie(response, new_refresh_token)
    return {
        "access_token": create_access_token(
            user["id"], next_version, mfa_verified=mfa_verified,
        ),
        "token_type": "bearer",
    }


@router.post("/mfa/setup")
async def setup_mfa(user: dict = Depends(get_current_user)):
    if user.get("role") != "superadmin":
        raise HTTPException(status_code=403, detail="MFA enrollment is restricted to administrators")
    if user.get("mfa_enabled"):
        raise HTTPException(status_code=409, detail="MFA is already enabled")
    secret = generate_secret()
    await db.users.update_one(
        {"id": user["id"]},
        {"$set": {"mfa_pending_secret": encrypt_secret(secret)}},
    )
    return {"secret": secret, "provisioning_uri": provisioning_uri(secret, user["email"])}


@router.post("/mfa/enable")
async def enable_mfa(
    body: MfaEnableIn,
    response: Response,
    user: dict = Depends(get_current_user),
):
    if user.get("role") != "superadmin":
        raise HTTPException(status_code=403, detail="MFA enrollment is restricted to administrators")
    pending = user.get("mfa_pending_secret")
    if not pending or not verify_totp(decrypt_secret(pending), body.otp):
        raise HTTPException(status_code=400, detail="Invalid authenticator code")
    next_version = int(user.get("auth_version", 0)) + 1
    await db.users.update_one(
        {"id": user["id"]},
        {
            "$set": {
                "mfa_secret": pending,
                "mfa_enabled": True,
                "mfa_enabled_at": datetime.now(timezone.utc).isoformat(),
                "auth_version": next_version,
            },
            "$unset": {"mfa_pending_secret": ""},
        },
    )
    await refresh_tokens.revoke_all(user["id"])
    new_refresh_token = await refresh_tokens.issue(user["id"], mfa_verified=True)
    _set_refresh_cookie(response, new_refresh_token)
    return {
        "access_token": create_access_token(user["id"], next_version, mfa_verified=True),
        "token_type": "bearer",
        "mfa_enabled": True,
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
        prefs = dict(user.get("default_alert_prefs") or {})
        prefs.update(body.default_alert_prefs.model_dump(exclude_none=True))
        updates["default_alert_prefs"] = prefs
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
    data = await export_account_data(db, user)
    return {"exported_at": datetime.now(timezone.utc).isoformat(), **data}


@router.delete("/me")
async def delete_my_account(response: Response, user: dict = Depends(get_current_user)):
    """Self-service account deletion (right to erasure / eliminação).

    Superadmin accounts are excluded — deleting your own admin access would
    be irreversible from inside the same session; another admin (or direct
    DB access) has to do it instead. Billing/payment records are kept for
    accounting and tax retention even though the account itself is erased;
    only the live subscription is canceled so nothing bills again.
    """
    if user.get("role") == "superadmin":
        raise HTTPException(status_code=400, detail="Superadmin accounts can't be self-deleted. Ask another admin to remove your access.")
    await cancel_subscription_for_deletion(user.get("stripe_subscription_id"))
    await erase_account_data(db, user)
    _clear_refresh_cookie(response)
    return {"ok": True}
