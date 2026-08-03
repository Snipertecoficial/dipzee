"""Small authenticated-encryption boundary for secrets persisted in MongoDB."""
import base64
import os
import secrets

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

_PREFIX = "enc:v1:"


def _key() -> bytes:
    encoded = os.environ.get("APP_ENCRYPTION_KEY", "")
    try:
        key = base64.b64decode(encoded, validate=True)
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError("APP_ENCRYPTION_KEY must be valid base64") from exc
    if len(key) != 32:
        raise RuntimeError("APP_ENCRYPTION_KEY must decode to exactly 32 bytes")
    return key


def encrypt_secret(value: str) -> str:
    if not value or value.startswith(_PREFIX):
        return value
    nonce = secrets.token_bytes(12)
    encrypted = AESGCM(_key()).encrypt(nonce, value.encode("utf-8"), b"dipzee-app-setting-v1")
    return _PREFIX + base64.b64encode(nonce + encrypted).decode("ascii")


def decrypt_secret(value: str) -> str:
    if not value:
        return value
    if not value.startswith(_PREFIX):
        raise RuntimeError("Refusing plaintext database secret; rotate or re-save it encrypted")
    try:
        payload = base64.b64decode(value[len(_PREFIX):], validate=True)
        return AESGCM(_key()).decrypt(payload[:12], payload[12:], b"dipzee-app-setting-v1").decode("utf-8")
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError("Stored application secret could not be decrypted") from exc


def is_encrypted_secret(value: str | None) -> bool:
    return bool(value and value.startswith(_PREFIX))
