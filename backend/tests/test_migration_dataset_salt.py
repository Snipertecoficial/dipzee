import asyncio
import importlib
import os

from tests.fakedb import FakeDB


migration = importlib.import_module("migrations.0002_rotate_legacy_dataset_pseudonyms")


def test_legacy_dataset_subjects_are_rotated_idempotently(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "legacy-jwt-secret-value-with-at-least-thirty-two-chars")
    monkeypatch.setenv("DATASET_SALT", "new-independent-dataset-salt-with-at-least-thirty-two-chars")
    db = FakeDB()
    db.users.docs = [{"id": "user-1"}, {"id": "user-2"}]
    legacy = migration._subject(os.environ["JWT_SECRET"], "user-1")
    current = migration._subject(os.environ["DATASET_SALT"], "user-1")
    db.inference_log.docs = [{"anon": legacy}, {"anon": current}, {"anon": None}]
    db.decision_log.docs = [{"anon": legacy}]

    asyncio.run(migration.up(db))
    asyncio.run(migration.up(db))

    assert [doc["anon"] for doc in db.inference_log.docs] == [current, current, None]
    assert db.decision_log.docs[0]["anon"] == current
