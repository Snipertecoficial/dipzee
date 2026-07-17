"""Auth helpers: password hashing, JWT, and the current-user dependency."""
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from passlib.context import CryptContext

from database import db
from plans import plan_capabilities, has_feature

logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ENV = os.environ.get("ENV", "development")
SECRET = os.environ.get("JWT_SECRET")
if not SECRET:
    if ENV == "production":
        raise RuntimeError("JWT_SECRET must be set in production (ENV=production).")
    SECRET = "insecure-dev-only-secret"
    logger.warning(
        "JWT_SECRET not set — using an insecure development-only fallback. "
        "This is NOT safe for production; set JWT_SECRET explicitly."
    )
ALGO = "HS256"
# Deliberately short-lived: this is a stateless JWT with no server-side
# revocation, so a stolen one is valid until it naturally expires no matter
# what. Long-lived sessions instead come from the revocable refresh token
# (see refresh_tokens.py) — the frontend transparently exchanges an expired
# access token for a new one via POST /auth/refresh.
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

bearer = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    # bcrypt has a 72-byte limit; truncate defensively.
    return pwd_context.hash(password[:72])


def verify_password(password: str, hashed: str) -> bool:
    try:
        return pwd_context.verify(password[:72], hashed)
    except Exception:
        return False


def create_access_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, SECRET, algorithm=ALGO)


def serialize_user(user: dict) -> dict:
    """Strip sensitive fields and ensure JSON-serializable output."""
    if not user:
        return user
    out = {k: v for k, v in user.items() if k not in ("hashed_password", "_id")}
    created = out.get("created_at")
    if isinstance(created, datetime):
        out["created_at"] = created.isoformat()
    # Attach plan capabilities so the frontend can gate features/upsells.
    out["capabilities"] = plan_capabilities(out.get("plan"))
    return out


def require_feature(feature: str):
    """Dependency factory: 403 unless the current user's plan has `feature`."""
    async def _dep(user: dict = Depends(get_current_user)) -> dict:
        if not has_feature(user.get("plan"), feature):
            raise HTTPException(
                status_code=403,
                detail={"code": "feature_locked", "feature": feature,
                        "message": f"Your plan does not include '{feature}'. Upgrade to unlock."},
            )
        return user
    return _dep


async def get_current_user(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(bearer),
) -> dict:
    if creds is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    token = creds.credentials
    try:
        payload = jwt.decode(token, SECRET, algorithms=[ALGO])
        user_id = payload.get("sub")
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user
