"""Auth routes: register, login, current user, profile/settings update."""
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field

from database import db
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


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    locale: str = "en"
    currency: str = "CAD"


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class ProfileIn(BaseModel):
    locale: Optional[str] = None
    currency: Optional[str] = None
    default_alert_prefs: Optional[dict] = None


def _auth_response(user: dict) -> dict:
    token = create_access_token(user["id"])
    return {"access_token": token, "token_type": "bearer", "user": serialize_user(user)}


@router.post("/register")
async def register(body: RegisterIn):
    email = body.email.lower()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=400, detail="Email already registered")
    locale = body.locale if body.locale in VALID_LOCALES else "en"
    currency = body.currency if body.currency in VALID_CURRENCIES else "CAD"
    user = {
        "id": str(uuid.uuid4()),
        "email": email,
        "hashed_password": hash_password(body.password),
        "locale": locale,
        "currency": currency,
        "plan": "free",
        "stripe_customer_id": None,
        "default_alert_prefs": {"email": True, "in_app": True},
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.users.insert_one(user)
    return _auth_response(user)


@router.post("/login")
async def login(body: LoginIn):
    user = await db.users.find_one({"email": body.email.lower()})
    if not user or not verify_password(body.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
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
    if updates:
        await db.users.update_one({"id": user["id"]}, {"$set": updates})
    fresh = await db.users.find_one({"id": user["id"]})
    return serialize_user(fresh)
