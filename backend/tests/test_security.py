"""Unit tests for auth primitives: password hashing, JWT, and user serialization.

No DB needed — these exercise the pure crypto/token helpers and the
serializer's sensitive-field stripping.
"""
from datetime import datetime, timedelta, timezone

import jwt
import pytest

from security import (
    hash_password, verify_password, create_access_token, serialize_user, SECRET, ALGO,
)


def test_password_hash_roundtrip():
    h = hash_password("abcd1234")
    assert h != "abcd1234"          # actually hashed
    assert verify_password("abcd1234", h) is True
    assert verify_password("wrong", h) is False


def test_password_hash_does_not_truncate_after_bcrypt_limit():
    first = "a" * 72 + "X9"
    second = "a" * 72 + "Y9"
    hashed = hash_password(first)
    assert verify_password(first, hashed) is True
    assert verify_password(second, hashed) is False


def test_verify_password_never_raises_on_garbage():
    # A malformed/empty hash must return False, not blow up (login path relies
    # on this for the dummy-hash timing defense).
    assert verify_password("x", "") is False
    assert verify_password("x", "not-a-bcrypt-hash") is False


def test_access_token_roundtrip():
    tok = create_access_token("user-123", auth_version=7)
    payload = jwt.decode(tok, SECRET, algorithms=[ALGO])
    assert payload["sub"] == "user-123"
    assert payload["ver"] == 7
    assert "exp" in payload


def test_expired_token_is_rejected():
    expired = jwt.encode(
        {"sub": "u", "exp": datetime.now(timezone.utc) - timedelta(minutes=1)},
        SECRET, algorithm=ALGO,
    )
    with pytest.raises(jwt.ExpiredSignatureError):
        jwt.decode(expired, SECRET, algorithms=[ALGO])


def test_alg_confusion_none_is_rejected():
    # A token signed with alg "none" must NOT be accepted — we pin algorithms.
    forged = jwt.encode({"sub": "admin"}, key="", algorithm="none")
    with pytest.raises(jwt.PyJWTError):
        jwt.decode(forged, SECRET, algorithms=[ALGO])


def test_serialize_user_strips_sensitive_fields():
    user = {
        "id": "u1", "email": "a@b.com", "hashed_password": "SECRET-HASH",
        "_id": "mongo-oid", "auth_version": 4, "plan": "pro", "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
    }
    out = serialize_user(user)
    assert "hashed_password" not in out and "_id" not in out and "auth_version" not in out
    assert out["email"] == "a@b.com"
    assert isinstance(out["created_at"], str)        # datetime -> ISO string
    assert out["capabilities"]["plan"] == "pro"      # capabilities attached
