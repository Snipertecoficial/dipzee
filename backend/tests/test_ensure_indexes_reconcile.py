"""Unit tests for the self-healing index helper ``database._create_index``.

Reproduces the exact production failure that blocked the deploy preflight: a
legacy *non-unique* ``token_hash_1`` already exists, and the code now declares
that index ``unique=True``. MongoDB rejects the recreate with an
IndexKeySpecsConflict (code 86). The helper must converge — drop the conflicting
same-key index and recreate it with the declared options — while re-raising any
unrelated failure so index creation stays a real readiness gate.

No live Mongo: a tiny async stub collection stands in (the suite's convention).
"""
import asyncio

import pytest
from pymongo.errors import OperationFailure

import database


def _run(coro):
    return asyncio.run(coro)


def _target(keys):
    return [(keys, 1)] if isinstance(keys, str) else list(keys)


class FakeCollection:
    """Async stand-in exposing just what ``_create_index`` touches."""

    def __init__(self, existing=None, conflict_code=None):
        # existing: {name: {'key': [(field, dir)], ...}}
        self._indexes = dict(existing or {})
        self._conflict_code = conflict_code   # raised on the FIRST create only
        self.created = []                     # [(keys, opts)] successful creates
        self.dropped = []                     # [name] dropped indexes

    async def create_index(self, keys, **opts):
        if self._conflict_code is not None:
            code = self._conflict_code
            self._conflict_code = None        # the conflict clears after a drop
            raise OperationFailure("index conflict", code, {})
        name = opts.get("name") or "_".join(
            f"{f}_{d}" for f, d in _target(keys)
        )
        self._indexes[name] = {"key": _target(keys), **{k: v for k, v in opts.items() if k != "name"}}
        self.created.append((keys, opts))
        return name

    async def index_information(self):
        return dict(self._indexes)

    async def drop_index(self, name):
        self.dropped.append(name)
        self._indexes.pop(name, None)


def test_identical_spec_passes_through():
    coll = FakeCollection()
    _run(database._create_index(coll, "email", unique=True))
    assert len(coll.created) == 1
    assert coll.dropped == []


def test_reconciles_legacy_non_unique_index():
    # Production condition: a non-unique token_hash_1 already exists; the code
    # now wants it unique -> code 86 on first create.
    coll = FakeCollection(
        existing={"token_hash_1": {"key": [("token_hash", 1)]}},   # non-unique
        conflict_code=86,
    )
    _run(database._create_index(coll, "token_hash", unique=True))
    assert coll.dropped == ["token_hash_1"]          # legacy index removed
    assert coll.created == [("token_hash", {"unique": True})]  # recreated unique
    assert coll._indexes["token_hash_1"]["unique"] is True


def test_reconciles_option_conflict_code_85():
    # IndexOptionsConflict (85) on a composite key must reconcile the same way.
    keys = [("user_id", 1), ("ticker", 1)]
    coll = FakeCollection(
        existing={"user_id_1_ticker_1": {"key": keys}},   # was non-unique
        conflict_code=85,
    )
    _run(database._create_index(coll, keys, unique=True))
    assert coll.dropped == ["user_id_1_ticker_1"]
    assert coll.created and coll.created[0][1] == {"unique": True}


def test_unrelated_failure_reraises():
    # A duplicate-key error (11000) is NOT an options conflict: it signals real
    # data that must be surfaced, never silently dropped-and-recreated.
    coll = FakeCollection(conflict_code=11000)
    with pytest.raises(OperationFailure):
        _run(database._create_index(coll, "token_hash", unique=True))
    assert coll.dropped == []      # never touched the existing index
