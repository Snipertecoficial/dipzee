"""Unit tests for the proprietary dataset + inference logging (L5).

Verifies the privacy guarantees (pseudonym is stable, one-way, PII-free),
best-effort logging, retention prune, right-to-erasure purge, and status — all
against the fake in-memory DB.
"""
import asyncio

import pytest

import dataset_service as ds
from tests.fakedb import FakeDB


def _run(coro):
    return asyncio.run(coro)


USER = {"id": "user-123", "plan": "pro", "locale": "en", "email": "someone@example.com"}


@pytest.fixture(autouse=True)
def _salt(monkeypatch):
    monkeypatch.setenv("DATASET_SALT", "test-salt")
    yield


# --- pseudonymization ------------------------------------------------------- #

def test_anon_stable_and_oneway():
    a = ds.anon_subject("user-123")
    assert a == ds.anon_subject("user-123")            # stable
    assert a != ds.anon_subject("user-999")            # distinct per user
    assert a.startswith("u_") and "user-123" not in a  # not reversible/plaintext
    assert ds.anon_subject("") == "anon"


# --- inference logging: no PII, training-pair shape ------------------------- #

def test_log_inference_stores_pair_without_pii():
    db = FakeDB()
    _run(ds.log_inference(db, "intel_asset", "aapl",
                          {"opportunity_score": 72, "net_impact": 0.3},
                          {"stance": "accumulate"}, model="claude", user=USER))
    rows = _run(db.inference_log.find({}).to_list(10))
    assert len(rows) == 1
    row = rows[0]
    assert row["kind"] == "intel_asset" and row["subject"] == "AAPL"
    assert row["context"]["opportunity_score"] == 72
    assert row["output"]["stance"] == "accumulate"
    assert row["anon"] == ds.anon_subject("user-123")
    # No PII leaked anywhere in the record.
    assert "someone@example.com" not in str(row) and "user-123" not in str(row)


def test_log_inference_never_raises_on_bad_db():
    class Boom:
        def __getattr__(self, _):
            raise RuntimeError("db down")
    # Must swallow the error (logging can't break the request path).
    _run(ds.log_inference(Boom(), "intel_asset", "AAPL", {}, {}, user=USER))


def test_log_decision_anonymized():
    db = FakeDB()
    _run(ds.log_decision(db, "watchlist_add", "msft", user=USER, meta={"src": "test"}))
    row = _run(db.decision_log.find_one({}))
    assert row["action"] == "watchlist_add" and row["subject"] == "MSFT"
    assert row["anon"] == ds.anon_subject("user-123") and row["meta"] == {"src": "test"}


# --- retention prune + erasure ---------------------------------------------- #

def test_prune_old_removes_only_expired():
    db = FakeDB()
    _run(db.inference_log.insert_one({"ts": "2000-01-01T00:00:00+00:00", "kind": "intel_asset"}))
    _run(db.inference_log.insert_one({"ts": "2999-01-01T00:00:00+00:00", "kind": "intel_asset"}))
    res = _run(ds.prune_old(db, retention_days=30))
    assert res["removed"]["inference_log"] == 1
    remaining = _run(db.inference_log.find({}).to_list(10))
    assert len(remaining) == 1 and remaining[0]["ts"].startswith("2999")


def test_purge_user_erases_pseudonym():
    db = FakeDB()
    _run(ds.log_inference(db, "ai_analyst", "AAPL", {}, {}, user=USER))
    _run(ds.log_decision(db, "watchlist_add", "AAPL", user=USER))
    _run(ds.log_decision(db, "watchlist_add", "AAPL", user={"id": "other", "plan": "pro"}))
    res = _run(ds.purge_user(db, "user-123"))
    assert res["removed"]["inference_log"] == 1 and res["removed"]["decision_log"] == 1
    # The other user's record survives.
    assert _run(db.decision_log.count_documents({})) == 1


def test_dataset_status_counts():
    db = FakeDB()
    _run(ds.log_inference(db, "intel_asset", "AAPL", {}, {}, user=USER))
    _run(ds.log_inference(db, "ai_analyst", "MSFT", {}, {}, user=USER))
    st = _run(ds.dataset_status(db))
    assert st["inferences"] == 2
    assert st["by_kind"]["intel_asset"] == 1 and st["by_kind"]["ai_analyst"] == 1
