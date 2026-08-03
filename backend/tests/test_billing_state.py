"""Unit tests for the billing state machine and the double-charge guard.

These exercise the money path with a fake in-memory DB and NEVER touch Stripe
(no stripe.* call is reached in any path tested here). Async functions are
driven via asyncio.run since the image has no pytest-asyncio.
"""
import asyncio

import pytest
from fastapi import HTTPException

import routes_billing
from tests.fakedb import FakeDB


def _run(coro):
    return asyncio.run(coro)


@pytest.fixture
def fake_db(monkeypatch):
    db = FakeDB()
    monkeypatch.setattr(routes_billing, "db", db)
    return db


# --- _apply_subscription_state: the core money-state machine ---------------- #

def test_active_subscription_grants_plan(fake_db):
    _run(fake_db.users.insert_one({"id": "u1", "role": "user", "plan": "none"}))
    _run(routes_billing._apply_subscription_state("u1", "pro", {"id": "sub_1", "status": "active"}))
    user = _run(fake_db.users.find_one({"id": "u1"}))
    assert user["plan"] == "pro"
    assert user["subscription_status"] == "active"
    assert user["stripe_subscription_id"] == "sub_1"


def test_past_due_fails_closed_and_disables_alerts(fake_db):
    _run(fake_db.users.insert_one({"id": "u1", "role": "user", "plan": "pro"}))
    _run(fake_db.alerts.insert_one({"id": "a1", "user_id": "u1", "active": True}))
    _run(routes_billing._apply_subscription_state("u1", "pro", {"id": "sub_1", "status": "past_due"}))
    user = _run(fake_db.users.find_one({"id": "u1"}))
    alert = _run(fake_db.alerts.find_one({"id": "a1"}))
    assert user["plan"] == "none"
    assert user["subscription_status"] == "past_due"
    assert alert["active"] is False


def test_canceled_downgrades_to_none(fake_db):
    _run(fake_db.users.insert_one({"id": "u1", "role": "user", "plan": "pro"}))
    _run(routes_billing._apply_subscription_state("u1", "pro", {"id": "sub_1", "status": "canceled"}))
    user = _run(fake_db.users.find_one({"id": "u1"}))
    assert user["plan"] == "none"


def test_canceled_never_downgrades_superadmin(fake_db):
    _run(fake_db.users.insert_one({"id": "admin1", "role": "superadmin", "plan": "investor"}))
    _run(routes_billing._apply_subscription_state("admin1", "investor", {"id": "sub_1", "status": "canceled"}))
    user = _run(fake_db.users.find_one({"id": "admin1"}))
    assert user["plan"] == "investor"


def test_session_txn_marked_paid_on_active(fake_db):
    _run(fake_db.users.insert_one({"id": "u1", "role": "user", "plan": "none"}))
    _run(fake_db.payment_transactions.insert_one({"id": "t1", "session_id": "cs_1", "processed": False}))
    sub = {
        "id": "sub_1",
        "status": "active",
        "latest_invoice": {"id": "in_1", "payment_intent": {"id": "pi_1"}},
    }
    _run(routes_billing._apply_subscription_state("u1", "pro", sub, session_id="cs_1"))
    tx = _run(fake_db.payment_transactions.find_one({"session_id": "cs_1"}))
    assert tx["payment_status"] == "paid"
    assert tx["payment_intent_id"] == "pi_1"
    assert tx["processed"] is True


def test_older_subscription_event_cannot_overwrite_newer_state(fake_db):
    _run(fake_db.users.insert_one({"id": "u1", "role": "user", "plan": "none"}))
    _run(routes_billing._apply_subscription_state(
        "u1", "pro", {"id": "sub_1", "status": "canceled"},
        event_created=200, event_id="evt_new",
    ))
    applied = _run(routes_billing._apply_subscription_state(
        "u1", "pro", {"id": "sub_1", "status": "active"},
        event_created=100, event_id="evt_old",
    ))
    user = _run(fake_db.users.find_one({"id": "u1"}))
    assert applied is False
    assert user["plan"] == "none"


# --- create_checkout: server-side double-charge guard ----------------------- #

def test_checkout_blocks_existing_active_subscriber(fake_db, monkeypatch):
    monkeypatch.setattr(routes_billing, "_ensure_configured", lambda: "sk_test")
    _run(fake_db.users.insert_one({"id": "u1", "stripe_subscription_id": "sub_1", "subscription_status": "active"}))
    body = routes_billing.CheckoutIn(package_id="pro_monthly")
    with pytest.raises(HTTPException) as exc:
        _run(routes_billing.create_checkout(body, {"id": "u1"}))
    assert exc.value.status_code == 409


def test_checkout_allowed_after_cancellation(fake_db, monkeypatch):
    monkeypatch.setattr(routes_billing, "_ensure_configured", lambda: "sk_test")

    # A user whose sub was canceled must be able to buy again. Prove the guard
    # passes by short-circuiting right after it with a sentinel — so we never
    # reach a real Stripe call, and a raised sentinel means the 409 did NOT fire.
    class _Sentinel(Exception):
        pass

    async def _boom(_user):
        raise _Sentinel()

    monkeypatch.setattr(routes_billing, "_get_or_create_customer", _boom)
    _run(fake_db.users.insert_one({"id": "u1", "stripe_subscription_id": "sub_old", "subscription_status": "canceled"}))
    body = routes_billing.CheckoutIn(package_id="pro_monthly")
    with pytest.raises(_Sentinel):
        _run(routes_billing.create_checkout(body, {"id": "u1"}))
