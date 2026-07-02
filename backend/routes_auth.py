"""Auth routes: register, login, current user, profile/settings update."""
import re
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field

from database import db
import login_guard
from security import (
    create_access_token,
    get_current_user,
    hash_password,
    serialize_user,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])

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


class LoginIn(BaseModel):
    email: EmailStr
    password: str


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


def _auth_response(user: dict) -> dict:
    token = create_access_token(user["id"])
    return {"access_token": token, "token_type": "bearer", "user": serialize_user(user)}


@router.post("/register")
async def register(body: RegisterIn):
    email = body.email.lower()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=400, detail="Email already registered")
    locale = body.locale if body.locale in VALID_LOCALES else "en"
    currency = body.currency if body.currency in VALID_CURRENCIES else "USD"
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
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.users.insert_one(user)
    return _auth_response(user)


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
    if not user or not verify_password(body.password, user["hashed_password"]):
        await login_guard.record_failure(email)
        raise HTTPException(status_code=401, detail="Invalid email or password")
    await login_guard.record_success(email)
    return _auth_response(user)


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
    for field in ("display_name", "bio", "phone", "country", "telegram_chat_id", "webhook_url"):
        val = getattr(body, field)
        if val is not None:
            updates[field] = _sanitize_text(val)
    if body.avatar is not None:
        av = body.avatar.strip()
        if av and not av.startswith("data:image/"):
            raise HTTPException(status_code=400, detail="Avatar must be a base64 image data URL")
        if len(av) > MAX_AVATAR_CHARS:
            raise HTTPException(status_code=413, detail={"code": "avatar_too_large", "message": "Image too large (max ~1.4MB)."})
        updates["avatar"] = av or None
    if updates:
        await db.users.update_one({"id": user["id"]}, {"$set": updates})
    fresh = await db.users.find_one({"id": user["id"]})
    return serialize_user(fresh)
