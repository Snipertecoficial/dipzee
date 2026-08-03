"""Auth helpers: password hashing, JWT, and the current-user dependency."""
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
import bcrypt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from database import db
from plans import plan_capabilities, has_feature

logger = logging.getLogger(__name__)

password_hasher = PasswordHasher(
    time_cost=3,
    memory_cost=65536,
    parallelism=2,
    hash_len=32,
    salt_len=16,
)

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
    return password_hasher.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    try:
        if hashed.startswith("$argon2"):
            return password_hasher.verify(hashed, password)
        if hashed.startswith(("$2a$", "$2b$", "$2y$")):
            # Legacy bcrypt accounts are upgraded to Argon2id immediately
            # after login. Truncation is limited to verifying those historical
            # hashes, whose format could never represent bytes beyond 72.
            return bcrypt.checkpw(password.encode("utf-8")[:72], hashed.encode("ascii"))
        return False
    except (ValueError, TypeError, VerificationError, VerifyMismatchError, InvalidHashError):
        return False


def password_needs_rehash(hashed: str) -> bool:
    try:
        return not hashed.startswith("$argon2") or password_hasher.check_needs_rehash(hashed)
    except (InvalidHashError, VerificationError):
        return True


def create_access_token(user_id: str, auth_version: int = 0, *, mfa_verified: bool = False) -> str:
    payload = {
        "sub": user_id,
        # Server-side epoch: password changes, reset and "logout all" bump the
        # user's value, invalidating already-issued access JWTs immediately.
        "ver": int(auth_version or 0),
        "mfa": bool(mfa_verified),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, SECRET, algorithm=ALGO)


def serialize_user(user: dict) -> dict:
    """Strip sensitive fields and ensure JSON-serializable output."""
    if not user:
        return user
    sensitive = {
        "hashed_password", "auth_version", "_id", "mfa_secret",
        "mfa_pending_secret", "_session_mfa_verified",
    }
    out = {k: v for k, v in user.items() if k not in sensitive and not k.startswith("_")}
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
        token_version = int(payload.get("ver", 0))
        mfa_verified = bool(payload.get("mfa", False))
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    if token_version != int(user.get("auth_version", 0)):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session revoked")
    user["_session_mfa_verified"] = mfa_verified
    return user
