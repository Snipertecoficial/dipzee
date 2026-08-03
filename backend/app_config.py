"""Validated public runtime configuration shared across HTTP domains."""
import os
import base64
from functools import lru_cache
from urllib.parse import urlparse


@lru_cache(maxsize=1)
def public_app_url() -> str:
    value = os.environ.get("PUBLIC_APP_URL", "").rstrip("/")
    env = os.environ.get("ENV", "development")
    if not value and env != "production":
        value = "http://localhost:3000"
    parsed = urlparse(value)
    if not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise RuntimeError("PUBLIC_APP_URL must be an absolute origin without credentials, query or fragment")
    if env == "production" and parsed.scheme != "https":
        raise RuntimeError("PUBLIC_APP_URL must use HTTPS in production")
    if parsed.scheme not in {"http", "https"}:
        raise RuntimeError("PUBLIC_APP_URL must use HTTP or HTTPS")
    return value


def validate_production_config() -> None:
    if os.environ.get("ENV", "development") != "production":
        return
    required = (
        "JWT_SECRET", "PUBLIC_APP_URL", "CORS_ORIGINS", "APP_ENCRYPTION_KEY",
        "BACKUP_ENCRYPTION_KEY", "STRIPE_API_KEY", "STRIPE_PUBLISHABLE_KEY",
        "STRIPE_WEBHOOK_SECRET", "SUPERADMIN_EMAIL", "SUPERADMIN_PASSWORD",
        "DATASET_SALT", "RESEND_API_KEY",
    )
    missing = [name for name in required if not os.environ.get(name)]
    if missing:
        raise RuntimeError(f"Missing required production settings: {', '.join(missing)}")
    public_app_url()
    if len(os.environ["JWT_SECRET"]) < 32 or len(os.environ["DATASET_SALT"]) < 32:
        raise RuntimeError("JWT_SECRET and DATASET_SALT must each contain at least 32 characters")
    if len(os.environ["SUPERADMIN_PASSWORD"]) < 12:
        raise RuntimeError("SUPERADMIN_PASSWORD must contain at least 12 characters")
    for name in ("APP_ENCRYPTION_KEY", "BACKUP_ENCRYPTION_KEY"):
        try:
            decoded = base64.b64decode(os.environ[name], validate=True)
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"{name} must be valid base64") from exc
        if len(decoded) != 32:
            raise RuntimeError(f"{name} must decode to exactly 32 bytes")
    origins = [item.strip() for item in os.environ["CORS_ORIGINS"].split(",") if item.strip()]
    parsed_origins = [urlparse(item) for item in origins]
    if not origins or any(
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.path not in {"", "/"}
        or parsed.params
        or parsed.query
        or parsed.fragment
        for parsed in parsed_origins
    ):
        raise RuntimeError("CORS_ORIGINS must contain only explicit HTTPS origins in production")
    if os.environ.get("ADMIN_MFA_REQUIRED", "").lower() not in {"1", "true", "yes"}:
        raise RuntimeError("ADMIN_MFA_REQUIRED must be enabled in production")
