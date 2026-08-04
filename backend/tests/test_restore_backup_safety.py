import asyncio

import pytest

from scripts.restore_backup import _assert_empty_target, _collections
from tests.fakedb import FakeDB


def test_restore_refuses_nonempty_target_collection():
    db = FakeDB()
    db.users.docs = [{"_id": "existing"}]

    with pytest.raises(RuntimeError, match="Target database is not empty"):
        asyncio.run(_assert_empty_target(db, ["users", "alerts"]))


def test_restore_accepts_empty_target_collections():
    db = FakeDB()
    asyncio.run(_assert_empty_target(db, ["users", "schema_migrations"]))


def test_only_document_lists_are_restorable_collections():
    assert _collections({
        "_meta": {"created_at": "now"},
        "users": [{"_id": "u1"}],
        "invalid": {"_id": "not-a-list"},
    }) == [("users", [{"_id": "u1"}])]
