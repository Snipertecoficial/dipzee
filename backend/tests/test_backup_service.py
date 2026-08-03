import base64
import asyncio
import os

import pytest

import backup_service
from scripts.restore_backup import _read_payload


class _Cursor:
    def __init__(self, docs):
        self._docs = docs

    def __aiter__(self):
        self._iterator = iter(self._docs)
        return self

    async def __anext__(self):
        try:
            return next(self._iterator)
        except StopIteration as exc:
            raise StopAsyncIteration from exc


class _Collection:
    def __init__(self, docs):
        self._docs = docs

    def find(self, _filter):
        return _Cursor(self._docs)


class _Database:
    def __init__(self):
        self._collections = {
            "users": _Collection([{"_id": "u1", "email": "private@example.com"}]),
            "market_cache": _Collection([{"secret": "regenerable"}]),
        }

    async def list_collection_names(self):
        return list(self._collections)

    def __getitem__(self, name):
        return self._collections[name]


def test_backup_is_encrypted_authenticated_and_restorable(tmp_path, monkeypatch):
    key = base64.b64encode(os.urandom(32)).decode("ascii")
    monkeypatch.setenv("BACKUP_ENCRYPTION_KEY", key)
    monkeypatch.setattr(backup_service, "BACKUP_DIR", str(tmp_path))
    monkeypatch.setattr(backup_service, "db", _Database())
    monkeypatch.setattr(backup_service, "_s3_client", lambda: None)

    result = asyncio.run(backup_service.create_backup())
    backup_path = tmp_path / result["file"]
    raw = backup_path.read_bytes()

    assert raw.startswith(b"DIPZEEBK1")
    assert b"private@example.com" not in raw
    assert result["offsite"] is False
    payload = _read_payload(str(backup_path))
    assert payload["data"]["users"][0]["email"] == "private@example.com"
    assert "market_cache" not in payload["data"]

    tampered = tmp_path / "tampered.json.gz.enc"
    broken = bytearray(raw)
    broken[-17] ^= 1
    tampered.write_bytes(broken)
    with pytest.raises(Exception):
        _read_payload(str(tampered))
