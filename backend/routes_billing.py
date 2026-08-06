"""Stripe RECURRING subscriptions (native Stripe SDK).

Implements a 7-day free trial (card required upfront) across the three paid
tiers using Checkout Sessions in ``mode="subscription"`` with inline
``price_data`` (no pre-created Price IDs). Plan state is synced primarily via
polling ``/billing/status/{session_id}`` and, when a webhook secret is set,
also via ``/webhook/stripe`` (idempotent). Prices are defined SERVER-SIDE only.

Notes:
- The Stripe Python SDK is synchronous; blocking calls are executed in a
  worker thread via ``asyncio.to_thread`` to avoid blocking the event loop.
- A trial subscription's Checkout Session has ``payment_status`` =
  ``no_payment_required`` while ``status`` = ``complete``; therefore success is
  determined by the *subscription* status (``trialing``/``active``), not by
  ``payment_status``.
"""
import asyncio
import logging
import os
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from app_config import public_app_url
from database import db
from email_service import send_email
from plans import PLAN_RANK
from security import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(tags=["billing"])

CURRENCY = "usd"

# Server-side catalog. Amounts kept in USD (mirrors the pricing cards on the
# landing/upgrade pages). Annual ~= 20% off (10 months). Each plan/interval
# gets a 7-day free trial. unit_amount is computed in CENTS at request time.
PACKAGES = {
    "starter_monthly": {"amount": 4.97, "plan": "starter", "interval": "month", "trial_days": 7},
    "starter_annual": {"amount": 47.71, "plan": "starter", "interval": "year", "trial_days": 7},
    "pro_monthly": {"amount": 12.97, "plan": "pro", "interval": "month", "trial_days": 7},
    "pro_annual": {"amount": 124.51, "plan": "pro", "interval": "year", "trial_days": 7},
    "investor_monthly": {"amount": 24.99, "plan": "investor", "interval": "month", "trial_days": 7},
    "investor_annual": {"amount": 239.90, "plan": "investor", "interval": "year", "trial_days": 7},
}

_ENTITLED_SUB_STATES = {"trialing", "active"}
_NON_ENTITLED_SUB_STATES = {
    "past_due", "unpaid", "canceled", "incomplete", "incomplete_expired", "paused",
}
MAX_WEBHOOK_BYTES = 512 * 1024


def _amount_cents(pkg: dict) -> int:
    return int((Decimal(str(pkg["amount"])) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _ensure_configured() -> str:
    api_key = os.environ.get("STRIPE_API_KEY")
    if not api_key or api_key in ("", "sk_test_emergent"):
        raise HTTPException(status_code=503, detail="Billing not configured")
    stripe.api_key = api_key
    return api_key


async def cancel_subscription_for_deletion(sub_id: str | None) -> None:
    """Confirm Stripe cancellation before destructive account deletion.

    Failing closed avoids deleting the local owner record while a remote paid
    subscription can still renew with no account left to manage it.
    """
    if not sub_id:
        return
    _ensure_configured()
    try:
        await asyncio.to_thread(stripe.Subscription.cancel, sub_id)
    except stripe.error.StripeError as e:  # noqa: BLE001
        if getattr(e, "code", None) == "resource_missing":
            return
        logger.error("[stripe] account deletion cancellation failed for %s: %s", sub_id, getattr(e, "user_message", e))
        raise HTTPException(status_code=502, detail="Could not confirm subscription cancellation; account was not deleted")


async def _notify_payment_failed(user: dict) -> None:
    """Warn a customer their card was declined (in-app + email) so they can
    update it before losing access. Billing is account-critical, so this bypasses
    the market-alert channel gating and always attempts both channels. Best
    effort: a delivery failure must never break webhook processing."""
    if not user:
        return
    manage_url = f"{public_app_url().rstrip('/')}/app/settings"
    msg = ("Não conseguimos processar o pagamento da sua assinatura Dipzee. "
           "Atualize seu cartão em Configurações → Assinatura para manter o acesso.")
    try:
        await db.alert_events.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": user["id"],
            "ticker": None,
            "type": "billing_payment_failed",
            "message": msg,
            "url": manage_url,
            "hidden": False,
            "read": False,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
    except Exception as e:  # noqa: BLE001
        logger.warning("[billing] in-app payment-failed notice failed: %s", e)
    if user.get("email"):
        subject = "Dipzee • Falha no pagamento da assinatura"
        html = (
            "<div style='font-family:Inter,Arial,sans-serif;color:#0F1424'>"
            "<h2 style='color:#1A1F4D'>Dipzee</h2>"
            f"<p>{msg}</p>"
            f"<p><a href='{manage_url}' style='color:#16a34a'>Atualizar meu cartão</a></p>"
            "<p style='color:#5B6478;font-size:12px'>Se você já atualizou o pagamento, ignore este aviso.</p>"
            "</div>"
        )
        try:
            await asyncio.to_thread(send_email, user["email"], subject, html)
        except Exception as e:  # noqa: BLE001
            logger.warning("[billing] payment-failed email failed: %s", e)


def _ts_to_iso(ts) -> str | None:
    if not ts:
        return None
    try:
        return datetime.fromtimestamp(int(ts), tz=timezone.utc).isoformat()
    except Exception:  # noqa: BLE001
        return None


class CheckoutIn(BaseModel):
    package_id: str

    model_config = ConfigDict(extra="ignore")


class PortalIn(BaseModel):
    model_config = ConfigDict(extra="ignore")


class ChangePlanIn(BaseModel):
    package_id: str


@router.get("/billing/config")
async def billing_config():
    """Public billing config (never exposes the secret key)."""
    configured = bool(os.environ.get("STRIPE_API_KEY")) and os.environ.get("STRIPE_API_KEY") != "sk_test_emergent"
    return {
        "configured": configured,
        "publishable_key": os.environ.get("STRIPE_PUBLISHABLE_KEY", ""),
        "packages": PACKAGES,
        "currency": CURRENCY.upper(),
        "trial_days": 7,
    }


async def _get_or_create_customer(user: dict) -> str:
    """Return the user's Stripe customer id, creating one if needed."""
    existing = user.get("stripe_customer_id")
    if existing:
        return existing
    customer = await asyncio.to_thread(
        stripe.Customer.create,
        email=user.get("email"),
        name=user.get("display_name") or None,
        metadata={"user_id": user["id"]},
        idempotency_key=f"dipzee-customer-{user['id']}",
    )
    await db.users.update_one({"id": user["id"]}, {"$set": {"stripe_customer_id": customer.id}})
    return customer.id


@router.post("/billing/checkout")
async def create_checkout(body: CheckoutIn, user: dict = Depends(get_current_user)):
    _ensure_configured()
    pkg = PACKAGES.get(body.package_id)
    if not pkg:
        raise HTTPException(status_code=400, detail="Invalid package")

    # Never let an already-subscribed user start a second Checkout — that would
    # create an independent second subscription on the same customer and
    # double-bill them. Existing subscribers must switch tiers in place via
    # /billing/change-plan. The frontend already routes them there; this is the
    # server-side enforcement so a direct API call can't bypass it. Re-read the
    # live record (the Depends() user may be stale) and gate on the real Stripe
    # status, so a canceled/lapsed user CAN check out again.
    fresh = await db.users.find_one({"id": user["id"]})
    if (fresh or {}).get("stripe_subscription_id") and (fresh or {}).get("subscription_status") in _ENTITLED_SUB_STATES:
        raise HTTPException(
            status_code=409,
            detail="You already have an active subscription. Use change-plan to switch tiers.",
        )

    lock_id = f"checkout:{user['id']}"
    lock_token = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    await db.billing_operation_locks.delete_one({"_id": lock_id, "expires_at": {"$lt": now}})
    try:
        await db.billing_operation_locks.insert_one({
            "_id": lock_id,
            "token": lock_token,
            "expires_at": now + timedelta(minutes=3),
        })
    except DuplicateKeyError:
        raise HTTPException(status_code=409, detail="A billing operation is already in progress")

    intent = None
    try:
        intent = await db.payment_transactions.find_one({
            "user_id": user["id"], "package_id": body.package_id, "status": "creating",
        })
        if not intent:
            intent = {
                "id": str(uuid.uuid4()),
                "user_id": user["id"],
                "email": user.get("email"),
                "amount_cents": _amount_cents(pkg),
                "currency": CURRENCY,
                "plan": pkg["plan"],
                "interval": pkg["interval"],
                "package_id": body.package_id,
                "payment_status": "initiated",
                "status": "creating",
                "processed": False,
                "created_at": now.isoformat(),
            }
            await db.payment_transactions.insert_one(intent)

        customer_id = await _get_or_create_customer(fresh or user)
        origin = public_app_url()
        success_url = f"{origin}/app/upgrade?session_id={{CHECKOUT_SESSION_ID}}"
        cancel_url = f"{origin}/app/upgrade"
        metadata = {
            "user_id": user["id"],
            "plan": pkg["plan"],
            "interval": pkg["interval"],
            "package_id": body.package_id,
        }
        session = await asyncio.to_thread(
            stripe.checkout.Session.create,
            mode="subscription",
            customer=customer_id,
            client_reference_id=user["id"],
            line_items=[{
                "price_data": {
                    "currency": CURRENCY,
                    "unit_amount": _amount_cents(pkg),
                    "recurring": {"interval": pkg["interval"]},
                    "product_data": {
                        "name": f"Dipzee {pkg['plan'].capitalize()}",
                        "metadata": {"plan": pkg["plan"]},
                    },
                },
                "quantity": 1,
            }],
            subscription_data={
                "trial_period_days": int(pkg["trial_days"]),
                "metadata": metadata,
            },
            payment_method_collection="always",
            allow_promotion_codes=True,
            success_url=success_url,
            cancel_url=cancel_url,
            metadata=metadata,
            idempotency_key=f"dipzee-checkout-{intent['id']}",
        )
    except stripe.error.StripeError as e:  # noqa
        logger.warning("[stripe checkout] error: %s", getattr(e, "user_message", e))
        if intent:
            await db.payment_transactions.update_one(
                {"id": intent["id"], "user_id": user["id"]},
                {"$set": {"status": "failed", "processed": True, "failure_code": "stripe_checkout"}},
            )
        raise HTTPException(status_code=502, detail="Stripe error creating checkout")
    finally:
        await db.billing_operation_locks.delete_one({"_id": lock_id, "token": lock_token})

    await db.payment_transactions.update_one(
        {"id": intent["id"], "user_id": user["id"]},
        {"$set": {"session_id": session.id, "checkout_url": session.url, "status": "pending"}},
    )
    return {"url": session.url, "session_id": session.id}


def _charge_fields(sub: dict) -> dict:
    invoice = (sub or {}).get("latest_invoice")
    if not isinstance(invoice, dict):
        return {}
    payment_intent = invoice.get("payment_intent")
    pi_id = payment_intent.get("id") if isinstance(payment_intent, dict) else payment_intent
    result = {"invoice_id": invoice.get("id")}
    if pi_id:
        result["payment_intent_id"] = pi_id
    return {k: v for k, v in result.items() if v}


async def _apply_subscription_state(
    user_id: str,
    plan: str,
    sub: dict,
    session_id: str | None = None,
    *,
    session_payment_status: str | None = None,
    event_created: int | None = None,
    event_id: str | None = None,
):
    """Idempotently sync the user's plan from a subscription object.

    Only ``trialing`` and ``active`` grant capabilities. Every other Stripe
    state fails closed to the free plan (never downgrading a superadmin).
    """
    if not user_id:
        return
    status = (sub or {}).get("status")
    sub_id = (sub or {}).get("id")
    if event_created and sub_id:
        previous = await db.billing_subscriptions.find_one({"stripe_subscription_id": sub_id})
        if previous and int(previous.get("last_event_created") or 0) > int(event_created):
            return False
    updates = {
        "stripe_subscription_id": sub_id,
        "subscription_status": status,
        "trial_ends_at": _ts_to_iso((sub or {}).get("trial_end")),
        "current_period_end": _ts_to_iso((sub or {}).get("current_period_end")),
    }
    user = await db.users.find_one({"id": user_id})
    if not user:
        return
    if status in _ENTITLED_SUB_STATES and plan in PLAN_RANK and plan != "none":
        updates["plan"] = plan
    else:
        if user.get("role") != "superadmin":
            updates["plan"] = "none"
    await db.users.update_one({"id": user_id}, {"$set": updates})
    if updates.get("plan") == "none":
        await db.alerts.update_many(
            {"user_id": user_id, "active": True},
            {"$set": {"active": False, "disabled_reason": "subscription_inactive"}},
        )

    # Audit record.
    if sub_id:
        await db.billing_subscriptions.update_one(
            {"stripe_subscription_id": sub_id},
            {"$set": {
                "user_id": user_id,
                "plan": plan,
                "status": status,
                "trial_ends_at": updates["trial_ends_at"],
                "current_period_end": updates["current_period_end"],
                "updated_at": datetime.now(timezone.utc).isoformat(),
                **({"last_event_created": int(event_created)} if event_created else {}),
                **({"last_event_id": event_id} if event_id else {}),
            }},
            upsert=True,
        )
    if event_id:
        await db.billing_subscription_events.update_one(
            {"event_id": event_id},
            {"$setOnInsert": {
                "event_id": event_id, "stripe_subscription_id": sub_id,
                "user_id": user_id, "plan": plan, "status": status,
                "event_created": event_created,
                "recorded_at": datetime.now(timezone.utc).isoformat(),
            }},
            upsert=True,
        )
    if session_id:
        charge = _charge_fields(sub)
        payment_status = session_payment_status or (
            "paid" if status == "active" and charge.get("payment_intent_id") else
            "no_payment_required" if status == "trialing" else
            (status or "unknown")
        )
        await db.payment_transactions.update_one(
            {"session_id": session_id},
            {"$set": {
                "payment_status": payment_status,
                "status": "complete" if status in _ENTITLED_SUB_STATES else "closed",
                "subscription_status": status,
                "processed": status in _ENTITLED_SUB_STATES or status in _NON_ENTITLED_SUB_STATES,
                "stripe_subscription_id": sub_id,
                **charge,
            }},
        )
    return True


async def sync_transaction_status(tx: dict) -> dict:
    """Re-check ONE transaction's real Stripe status and sync it locally.

    This is what makes billing status reliable even when the customer never
    comes back to the app after paying (closed the tab, network hiccup) and
    the webhook either isn't configured or was missed — both the polling
    endpoint below AND this function converge on the same source of truth
    (Stripe), so a transaction can never get permanently stuck showing
    "initiated" just because neither happened to fire.
    """
    session_id = tx.get("session_id")
    if not session_id:
        return tx
    try:
        session = await asyncio.to_thread(
            stripe.checkout.Session.retrieve,
            session_id,
            expand=["subscription.latest_invoice.payment_intent"],
        )
    except stripe.error.StripeError as e:  # noqa
        logger.warning("[stripe sync] could not retrieve session %s: %s", session_id, e)
        return tx

    session_status = session.get("status")
    if session_status == "expired":
        await db.payment_transactions.update_one(
            {"id": tx["id"]},
            {"$set": {"payment_status": "expired", "status": "expired", "processed": True}},
        )
        return await db.payment_transactions.find_one({"id": tx["id"]}, {"_id": 0})

    sub = session.get("subscription")
    sub_dict = dict(sub) if sub else {}
    plan = (session.get("metadata") or {}).get("plan") or (sub_dict.get("metadata") or {}).get("plan")
    sub_status = sub_dict.get("status")
    complete = session_status == "complete"
    user_id = session.get("client_reference_id") or (session.get("metadata") or {}).get("user_id")

    if complete and plan and user_id:
        await _apply_subscription_state(
            user_id,
            plan,
            sub_dict,
            session_id=session_id,
            session_payment_status=session.get("payment_status"),
        )
    return await db.payment_transactions.find_one({"id": tx["id"]}, {"_id": 0})


async def reconcile_pending_transactions(max_age_days: int = 30) -> dict:
    """Sweep every transaction still marked unprocessed and sync it.

    Bounded to the last `max_age_days` — a checkout session Stripe has
    already expired (~24h after creation) is resolved to a terminal
    "expired" status well before that window closes, so anything older is
    either already resolved or genuinely abandoned and not worth re-checking
    forever.
    """
    api_key = os.environ.get("STRIPE_API_KEY")
    if not api_key or api_key in ("", "sk_test_emergent"):
        return {"checked": 0, "updated": 0}
    stripe.api_key = api_key

    cutoff = (datetime.now(timezone.utc) - timedelta(days=max_age_days)).isoformat()
    pending = await db.payment_transactions.find(
        {"processed": False, "created_at": {"$gte": cutoff}}
    ).to_list(500)

    updated = 0
    for tx in pending:
        before = tx.get("payment_status")
        after = await sync_transaction_status(tx)
        if after and after.get("payment_status") != before:
            updated += 1
    return {"checked": len(pending), "updated": updated}


async def reconcile_active_subscriptions() -> dict:
    """Backstop for missed SUBSCRIPTION-lifecycle webhooks.

    ``reconcile_pending_transactions`` only sweeps checkout transactions; a
    missed ``customer.subscription.deleted``/``updated`` (webhook down when it
    fired) would otherwise leave a user on a paid plan forever, or stuck
    ``past_due``. Here we re-read every user who currently looks active from
    Stripe directly and re-apply their real state — so plan state converges on
    Stripe even if a lifecycle webhook was never delivered.
    """
    api_key = os.environ.get("STRIPE_API_KEY")
    if not api_key or api_key in ("", "sk_test_emergent"):
        return {"checked": 0, "updated": 0}
    stripe.api_key = api_key

    users = await db.users.find(
        {"stripe_subscription_id": {"$nin": [None, ""]}}
    ).to_list(1000)

    updated = 0
    for u in users:
        sub_id = u.get("stripe_subscription_id")
        try:
            sub = await asyncio.to_thread(stripe.Subscription.retrieve, sub_id)
        except stripe.error.StripeError as e:  # noqa
            logger.warning("[billing reconcile] could not retrieve subscription %s: %s", sub_id, getattr(e, "user_message", e))
            continue
        sub_dict = dict(sub)
        before = u.get("subscription_status")
        plan = (sub_dict.get("metadata") or {}).get("plan") or u.get("plan")
        await _apply_subscription_state(u["id"], plan, sub_dict)
        if sub_dict.get("status") != before:
            updated += 1
    return {"checked": len(users), "updated": updated}


async def process_billing_outbox(limit: int = 50) -> dict:
    """Retry durable Stripe operations that failed after local state changed."""
    api_key = os.environ.get("STRIPE_API_KEY")
    if not api_key or api_key in ("", "sk_test_emergent"):
        return {"checked": 0, "completed": 0}
    stripe.api_key = api_key
    now = datetime.now(timezone.utc)
    # Recover work abandoned by a process crash before claiming new jobs.
    await db.billing_outbox.update_many(
        {"status": "processing", "lease_expires_at": {"$lte": now}},
        {"$set": {"status": "pending", "next_attempt_at": now},
         "$unset": {"lease_token": "", "lease_expires_at": ""}},
    )
    jobs = await db.billing_outbox.find({
        "status": "pending",
        "next_attempt_at": {"$lte": now},
    }).sort("next_attempt_at", 1).limit(max(1, min(limit, 100))).to_list(length=None)
    completed = 0
    for job in jobs:
        lease_token = str(uuid.uuid4())
        job = await db.billing_outbox.find_one_and_update(
            {
                "operation_id": job["operation_id"],
                "status": "pending",
                "next_attempt_at": {"$lte": now},
            },
            {"$set": {
                "status": "processing",
                "lease_token": lease_token,
                "lease_expires_at": now + timedelta(minutes=5),
            }},
            return_document=ReturnDocument.AFTER,
        )
        if not job:
            continue
        if job.get("operation") != "cancel_subscription":
            await db.billing_outbox.update_one(
                {"operation_id": job["operation_id"], "lease_token": lease_token},
                {"$set": {"status": "failed", "failure_reason": "unsupported_operation"},
                 "$unset": {"lease_token": "", "lease_expires_at": ""}},
            )
            continue
        sub_id = job.get("stripe_subscription_id")
        try:
            canceled = await asyncio.to_thread(stripe.Subscription.cancel, sub_id)
            await _apply_subscription_state(job.get("user_id"), "none", dict(canceled))
            await db.billing_outbox.update_one(
                {"operation_id": job["operation_id"], "lease_token": lease_token},
                {"$set": {
                    "status": "completed",
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                }, "$unset": {"lease_token": "", "lease_expires_at": ""}},
            )
            completed += 1
        except stripe.error.StripeError as e:  # noqa: BLE001
            if getattr(e, "code", None) == "resource_missing":
                await db.billing_outbox.update_one(
                    {"operation_id": job["operation_id"], "lease_token": lease_token},
                    {"$set": {"status": "completed", "completed_at": datetime.now(timezone.utc).isoformat()},
                     "$unset": {"lease_token": "", "lease_expires_at": ""}},
                )
                completed += 1
                continue
            attempts = int(job.get("attempts") or 0) + 1
            delay_minutes = min(24 * 60, 2 ** min(attempts, 10))
            logger.warning("[billing outbox] cancellation retry failed for %s: %s", sub_id, getattr(e, "user_message", e))
            await db.billing_outbox.update_one(
                {"operation_id": job["operation_id"], "lease_token": lease_token},
                {"$set": {
                    "status": "pending",
                    "attempts": attempts,
                    "next_attempt_at": now + timedelta(minutes=delay_minutes),
                }, "$unset": {"lease_token": "", "lease_expires_at": ""}},
            )
    return {"checked": len(jobs), "completed": completed}


async def refund_transaction_charge(tx: dict) -> dict:
    """Refund exactly the payment intent recorded for this transaction."""
    _ensure_configured()
    if tx.get("refunded"):
        return {"ok": True, "refund_id": tx.get("refund_id"), "status": tx.get("refund_status"), "duplicate": True}
    pi_id = tx.get("payment_intent_id")
    if not pi_id:
        raise HTTPException(
            status_code=409,
            detail="This legacy transaction has no recorded charge reference and requires manual verification",
        )

    try:
        refund = await asyncio.to_thread(
            stripe.Refund.create,
            payment_intent=pi_id,
            idempotency_key=f"dipzee-refund-{tx['id']}",
        )
    except stripe.error.StripeError as e:  # noqa
        logger.warning("[stripe refund] error: %s", getattr(e, "user_message", e))
        raise HTTPException(status_code=502, detail="Stripe refund could not be completed")

    await db.payment_transactions.update_one(
        {"id": tx["id"]},
        {"$set": {
            "refunded": True,
            "refund_id": refund.id,
            "refund_status": refund.status,
            "refunded_at": datetime.now(timezone.utc).isoformat(),
        }},
    )

    # Revoke local capabilities immediately. Remote cancellation is attempted
    # synchronously and persisted as an outbox job if Stripe is unavailable.
    sub_id = tx.get("stripe_subscription_id")
    user_id = tx.get("user_id")
    if user_id:
        target = await db.users.find_one({"id": user_id})
        if target and target.get("role") != "superadmin":
            await db.users.update_one(
                {"id": user_id},
                {"$set": {"plan": "none", "subscription_status": "refunded"}},
            )
            await db.alerts.update_many(
                {"user_id": user_id, "active": True},
                {"$set": {"active": False, "disabled_reason": "subscription_refunded"}},
            )

    cancellation_pending = False
    if sub_id:
        try:
            canceled = await asyncio.to_thread(stripe.Subscription.cancel, sub_id)
            await _apply_subscription_state(user_id, "none", dict(canceled))
        except stripe.error.StripeError as e:  # noqa
            logger.warning("[stripe refund] refunded but failed to cancel subscription %s: %s", sub_id, getattr(e, "user_message", e))
            if getattr(e, "code", None) != "resource_missing":
                cancellation_pending = True
                await db.billing_outbox.update_one(
                    {"operation_id": f"cancel:{sub_id}"},
                    {"$set": {
                        "operation_id": f"cancel:{sub_id}",
                        "operation": "cancel_subscription",
                        "stripe_subscription_id": sub_id,
                        "user_id": user_id,
                        "status": "pending",
                        "attempts": 0,
                        "next_attempt_at": datetime.now(timezone.utc),
                        "created_at": datetime.now(timezone.utc).isoformat(),
                    }},
                    upsert=True,
                )

    return {
        "ok": True,
        "refund_id": refund.id,
        "status": refund.status,
        "cancellation_pending": cancellation_pending,
    }


@router.get("/billing/status/{session_id}")
async def checkout_status(session_id: str, user: dict = Depends(get_current_user)):
    _ensure_configured()
    try:
        session = await asyncio.to_thread(
            stripe.checkout.Session.retrieve,
            session_id,
            expand=["subscription.latest_invoice.payment_intent"],
        )
    except stripe.error.StripeError as e:  # noqa
        logger.warning("[stripe status] error: %s", getattr(e, "user_message", e))
        raise HTTPException(status_code=502, detail="Stripe error")

    # A session_id is not a secret — it rides in a plain success-URL query
    # string and can leak via browser history, referrers, or screenshots.
    # Without this check, anyone who obtains someone else's session_id could
    # call this endpoint as themselves and have that person's paid plan
    # granted to their OWN account for free.
    owner_id = session.get("client_reference_id") or (session.get("metadata") or {}).get("user_id")
    if owner_id != user["id"]:
        raise HTTPException(status_code=403, detail="This checkout session does not belong to you")

    sub = session.get("subscription")
    sub_dict = dict(sub) if sub else {}
    plan = (session.get("metadata") or {}).get("plan") or (sub_dict.get("metadata") or {}).get("plan")
    sub_status = sub_dict.get("status")
    complete = session.get("status") == "complete"
    active = complete and sub_status in _ENTITLED_SUB_STATES

    if complete and plan:
        await _apply_subscription_state(
            user["id"],
            plan,
            sub_dict,
            session_id=session_id,
            session_payment_status=session.get("payment_status"),
        )

    fresh = await db.users.find_one(
        {"id": user["id"]},
        {"_id": 0, "hashed_password": 0, "auth_version": 0},
    )
    return {
        "session_status": session.get("status"),
        "payment_status": session.get("payment_status"),
        "subscription_status": sub_status,
        "active": bool(active),
        "plan": fresh.get("plan"),
        "trial_ends_at": _ts_to_iso(sub_dict.get("trial_end")),
    }


@router.get("/billing/subscription")
async def my_subscription(user: dict = Depends(get_current_user)):
    """Return the current user's subscription snapshot for UI display."""
    fresh = await db.users.find_one({"id": user["id"]})
    sub_id = (fresh or {}).get("stripe_subscription_id")
    data = {
        "plan": (fresh or {}).get("plan", "none"),
        "subscription_status": (fresh or {}).get("subscription_status"),
        "trial_ends_at": (fresh or {}).get("trial_ends_at"),
        "current_period_end": (fresh or {}).get("current_period_end"),
        "cancel_at_period_end": False,
        "has_subscription": bool(sub_id),
    }
    if sub_id and os.environ.get("STRIPE_API_KEY") not in (None, "", "sk_test_emergent"):
        _ensure_configured()
        try:
            sub = await asyncio.to_thread(stripe.Subscription.retrieve, sub_id)
            data["subscription_status"] = sub.get("status")
            data["cancel_at_period_end"] = bool(sub.get("cancel_at_period_end"))
            data["current_period_end"] = _ts_to_iso(sub.get("current_period_end"))
            data["trial_ends_at"] = _ts_to_iso(sub.get("trial_end"))
        except stripe.error.StripeError:  # noqa
            pass
    return data


@router.post("/billing/change-plan")
async def change_plan(body: ChangePlanIn, user: dict = Depends(get_current_user)):
    """Upgrade or downgrade an existing subscription IN PLACE.

    Deliberately does not go through Checkout: creating a new Checkout
    Session for a user who already has an active subscription would start a
    second, independent Stripe subscription (and double-bill them) instead of
    changing the existing one. Stripe prorates the price difference on the
    next invoice automatically.
    """
    _ensure_configured()
    pkg = PACKAGES.get(body.package_id)
    if not pkg:
        raise HTTPException(status_code=400, detail="Invalid package")

    fresh = await db.users.find_one({"id": user["id"]})
    sub_id = (fresh or {}).get("stripe_subscription_id")
    if not sub_id:
        raise HTTPException(status_code=400, detail="No active subscription to change")

    try:
        current = await asyncio.to_thread(stripe.Subscription.retrieve, sub_id)
    except stripe.error.StripeError as e:  # noqa
        logger.warning("[stripe change-plan] retrieve error: %s", getattr(e, "user_message", e))
        raise HTTPException(status_code=502, detail="Stripe error")

    if current.get("status") not in _ENTITLED_SUB_STATES:
        raise HTTPException(status_code=400, detail="Subscription is not active")

    item = current["items"]["data"][0]
    current_interval = ((item.get("price") or {}).get("recurring") or {}).get("interval")
    if (current.get("metadata") or {}).get("plan") == pkg["plan"] and current_interval == pkg["interval"]:
        raise HTTPException(status_code=400, detail="Already on this plan")

    unit_amount = _amount_cents(pkg)
    metadata = {"user_id": user["id"], "plan": pkg["plan"], "interval": pkg["interval"], "package_id": body.package_id}

    try:
        updated = await asyncio.to_thread(
            stripe.Subscription.modify,
            sub_id,
            items=[{
                "id": item["id"],
                "price_data": {
                    "currency": CURRENCY,
                    "unit_amount": unit_amount,
                    "recurring": {"interval": pkg["interval"]},
                    "product_data": {
                        "name": f"Dipzee {pkg['plan'].capitalize()}",
                        "metadata": {"plan": pkg["plan"]},
                    },
                },
            }],
            proration_behavior="create_prorations",
            metadata=metadata,
            cancel_at_period_end=False,
        )
    except stripe.error.StripeError as e:  # noqa
        logger.warning("[stripe change-plan] modify error: %s", getattr(e, "user_message", e))
        raise HTTPException(status_code=502, detail="Stripe error changing plan")

    await _apply_subscription_state(user["id"], pkg["plan"], dict(updated))
    return await my_subscription(user)


@router.post("/billing/cancel")
async def cancel_subscription(user: dict = Depends(get_current_user)):
    """Cancel at the end of the current billing period.

    The customer keeps the plan they already paid for until it lapses, and
    is never charged again — no proration/refund complexity.
    """
    _ensure_configured()
    fresh = await db.users.find_one({"id": user["id"]})
    sub_id = (fresh or {}).get("stripe_subscription_id")
    if not sub_id:
        raise HTTPException(status_code=400, detail="No active subscription")
    try:
        await asyncio.to_thread(stripe.Subscription.modify, sub_id, cancel_at_period_end=True)
    except stripe.error.StripeError as e:  # noqa
        logger.warning("[stripe cancel] error: %s", getattr(e, "user_message", e))
        raise HTTPException(status_code=502, detail="Stripe error canceling subscription")
    return await my_subscription(user)


@router.post("/billing/reactivate")
async def reactivate_subscription(user: dict = Depends(get_current_user)):
    """Undo a pending cancel-at-period-end before it takes effect."""
    _ensure_configured()
    fresh = await db.users.find_one({"id": user["id"]})
    sub_id = (fresh or {}).get("stripe_subscription_id")
    if not sub_id:
        raise HTTPException(status_code=400, detail="No active subscription")
    try:
        await asyncio.to_thread(stripe.Subscription.modify, sub_id, cancel_at_period_end=False)
    except stripe.error.StripeError as e:  # noqa
        logger.warning("[stripe reactivate] error: %s", getattr(e, "user_message", e))
        raise HTTPException(status_code=502, detail="Stripe error reactivating subscription")
    return await my_subscription(user)


@router.post("/billing/portal")
async def billing_portal(body: PortalIn, user: dict = Depends(get_current_user)):
    _ensure_configured()
    fresh = await db.users.find_one({"id": user["id"]})
    customer_id = (fresh or {}).get("stripe_customer_id")
    if not customer_id:
        raise HTTPException(status_code=400, detail="No billing account for this user")
    return_url = f"{public_app_url()}/app/settings"

    async def _create(config_id: str | None = None):
        kwargs = {"customer": customer_id, "return_url": return_url}
        if config_id:
            kwargs["configuration"] = config_id
        return await asyncio.to_thread(stripe.billing_portal.Session.create, **kwargs)

    try:
        session = await _create()
    except stripe.error.StripeError as e:  # noqa
        # In TEST mode the portal may have no default configuration yet;
        # create a minimal one on the fly and retry once.
        logger.info("[stripe portal] creating default configuration: %s", getattr(e, "user_message", e))
        try:
            config = await asyncio.to_thread(
                stripe.billing_portal.Configuration.create,
                business_profile={"headline": "Dipzee"},
                features={
                    "invoice_history": {"enabled": True},
                    "payment_method_update": {"enabled": True},
                    "customer_update": {"enabled": True, "allowed_updates": ["email", "address"]},
                    "subscription_cancel": {"enabled": True, "mode": "at_period_end"},
                },
            )
            session = await _create(config.id)
        except stripe.error.StripeError as e2:  # noqa
            logger.warning("[stripe portal] error: %s", getattr(e2, "user_message", e2))
            raise HTTPException(status_code=502, detail="Stripe error creating portal session")
    return {"url": session.url}


@router.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    _ensure_configured()
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > MAX_WEBHOOK_BYTES:
                raise HTTPException(status_code=413, detail="Webhook payload too large")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid Content-Length")
    payload = await request.body()
    if len(payload) > MAX_WEBHOOK_BYTES:
        raise HTTPException(status_code=413, detail="Webhook payload too large")
    sig = request.headers.get("Stripe-Signature")
    secret = os.environ.get("STRIPE_WEBHOOK_SECRET")

    if not secret:
        logger.error("[stripe webhook] STRIPE_WEBHOOK_SECRET not configured — refusing unsigned payload.")
        raise HTTPException(status_code=503, detail="Webhook not configured")

    try:
        event = stripe.Webhook.construct_event(payload, sig, secret)
    except Exception as e:  # noqa: BLE001
        logger.warning("[stripe webhook] signature verify failed: %s", e)
        raise HTTPException(status_code=400, detail="Invalid signature")

    event_id = event.get("id") if isinstance(event, dict) else getattr(event, "id", None)
    event_type = event.get("type") if isinstance(event, dict) else getattr(event, "type", None)
    event_created = event.get("created") if isinstance(event, dict) else getattr(event, "created", None)
    lease_token = str(uuid.uuid4())

    # Claim the event before executing side effects. A unique event_id index
    # turns concurrent deliveries into one winner; failed handlers release the
    # claim so Stripe can safely retry.
    if event_id:
        try:
            await db.stripe_events.insert_one({
                "event_id": event_id,
                "type": event_type,
                "status": "processing",
                "lease_token": lease_token,
                "lease_expires_at": datetime.now(timezone.utc) + timedelta(minutes=5),
                "created_at": datetime.now(timezone.utc).isoformat(),
                "purge_at": datetime.now(timezone.utc) + timedelta(days=90),
            })
        except DuplicateKeyError:
            already = await db.stripe_events.find_one({"event_id": event_id})
            if already and already.get("status") == "processed":
                return {"received": True, "duplicate": True}
            reclaimed = await db.stripe_events.update_one(
                {
                    "event_id": event_id,
                    "status": "processing",
                    "lease_expires_at": {"$lte": datetime.now(timezone.utc)},
                },
                {"$set": {
                    "lease_token": lease_token,
                    "lease_expires_at": datetime.now(timezone.utc) + timedelta(minutes=5),
                }},
            )
            if not reclaimed.modified_count:
                raise HTTPException(status_code=409, detail="Webhook event is already processing")

    data_obj = (event.get("data") or {}).get("object") if isinstance(event, dict) else event.data.object
    data_obj = dict(data_obj) if data_obj else {}

    try:
        if event_type == "checkout.session.completed":
            sub_id = data_obj.get("subscription")
            user_id = data_obj.get("client_reference_id") or (data_obj.get("metadata") or {}).get("user_id")
            plan = (data_obj.get("metadata") or {}).get("plan")
            if sub_id:
                sub = await asyncio.to_thread(
                    stripe.Subscription.retrieve,
                    sub_id,
                    expand=["latest_invoice.payment_intent"],
                )
                plan = plan or (sub.get("metadata") or {}).get("plan")
                await _apply_subscription_state(
                    user_id,
                    plan,
                    dict(sub),
                    session_id=data_obj.get("id"),
                    session_payment_status=data_obj.get("payment_status"),
                    event_created=event_created,
                    event_id=event_id,
                )
        elif event_type in ("customer.subscription.updated", "customer.subscription.created",
                            "customer.subscription.deleted"):
            plan = (data_obj.get("metadata") or {}).get("plan")
            user_id = (data_obj.get("metadata") or {}).get("user_id")
            if not user_id:
                u = await db.users.find_one({"stripe_customer_id": data_obj.get("customer")})
                user_id = u.get("id") if u else None
            await _apply_subscription_state(
                user_id,
                plan,
                data_obj,
                event_created=event_created,
                event_id=event_id,
            )
        elif event_type in ("invoice.paid", "invoice.payment_failed"):
            u = await db.users.find_one({"stripe_customer_id": data_obj.get("customer")})
            sub_id = data_obj.get("subscription")
            if event_type == "invoice.payment_failed":
                await _notify_payment_failed(u)
            payment_intent = data_obj.get("payment_intent")
            pi_id = payment_intent.get("id") if isinstance(payment_intent, dict) else payment_intent
            invoice_id = data_obj.get("id")
            if event_type == "invoice.paid" and u and invoice_id:
                await db.payment_transactions.update_one(
                    {"id": f"invoice:{invoice_id}"},
                    {
                        "$setOnInsert": {
                            "id": f"invoice:{invoice_id}",
                            "user_id": u["id"],
                            "email": u.get("email"),
                            "created_at": datetime.now(timezone.utc).isoformat(),
                        },
                        "$set": {
                            "invoice_id": invoice_id,
                            "payment_intent_id": pi_id,
                            "stripe_subscription_id": sub_id,
                            "amount_cents": int(data_obj.get("amount_paid") or 0),
                            "currency": data_obj.get("currency") or CURRENCY,
                            "plan": u.get("plan"),
                            "payment_status": "paid",
                            "status": "complete",
                            "processed": True,
                        },
                    },
                    upsert=True,
                )
            if u and sub_id:
                sub = await asyncio.to_thread(
                    stripe.Subscription.retrieve,
                    sub_id,
                    expand=["latest_invoice.payment_intent"],
                )
                plan = (sub.get("metadata") or {}).get("plan") or u.get("plan")
                await _apply_subscription_state(
                    u["id"],
                    plan,
                    dict(sub),
                    event_created=event_created,
                    event_id=event_id,
                )
        elif event_type == "checkout.session.expired":
            # Customer opened checkout but abandoned it — resolve the
            # transaction to a terminal state instead of leaving it stuck at
            # "initiated" forever in the billing panel.
            await db.payment_transactions.update_one(
                {"session_id": data_obj.get("id")},
                {"$set": {"payment_status": "expired", "status": "expired", "processed": True}},
            )
    except Exception as e:  # noqa: BLE001
        if event_id:
            await db.stripe_events.delete_one({"event_id": event_id, "lease_token": lease_token})
        logger.error("[stripe webhook] handler error (%s), returning 500 for retry: %s", event_type, e)
        raise HTTPException(status_code=500, detail="Webhook handler error")

    if event_id:
        await db.stripe_events.update_one(
            {"event_id": event_id, "lease_token": lease_token},
            {"$set": {
                "status": "processed",
                "processed_at": datetime.now(timezone.utc).isoformat(),
            }, "$unset": {"lease_token": "", "lease_expires_at": ""}},
        )

    return {"received": True}
