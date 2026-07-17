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

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from database import db
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

_ACTIVE_SUB_STATES = {"trialing", "active", "past_due"}


def _ensure_configured() -> str:
    api_key = os.environ.get("STRIPE_API_KEY")
    if not api_key or api_key in ("", "sk_test_emergent"):
        raise HTTPException(status_code=503, detail="Billing not configured")
    stripe.api_key = api_key
    return api_key


async def cancel_subscription_silently(sub_id: str | None) -> None:
    """Best-effort Stripe cancellation for account deletion (self-service or
    admin-initiated). Never raises — deleting the account must succeed even if
    Stripe is unreachable or already in sync; a stray active subscription is
    logged so it can be cleaned up by hand rather than silently forgotten.
    """
    if not sub_id:
        return
    api_key = os.environ.get("STRIPE_API_KEY")
    if not api_key or api_key in ("", "sk_test_emergent"):
        return
    stripe.api_key = api_key
    try:
        await asyncio.to_thread(stripe.Subscription.cancel, sub_id)
    except Exception as e:  # noqa: BLE001
        logger.warning("[stripe] failed to cancel subscription %s during account deletion: %s", sub_id, e)


def _ts_to_iso(ts) -> str | None:
    if not ts:
        return None
    try:
        return datetime.fromtimestamp(int(ts), tz=timezone.utc).isoformat()
    except Exception:  # noqa: BLE001
        return None


class CheckoutIn(BaseModel):
    package_id: str
    origin_url: str


class PortalIn(BaseModel):
    origin_url: str


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
    )
    await db.users.update_one({"id": user["id"]}, {"$set": {"stripe_customer_id": customer.id}})
    return customer.id


@router.post("/billing/checkout")
async def create_checkout(body: CheckoutIn, user: dict = Depends(get_current_user)):
    _ensure_configured()
    pkg = PACKAGES.get(body.package_id)
    if not pkg:
        raise HTTPException(status_code=400, detail="Invalid package")

    customer_id = await _get_or_create_customer(user)
    origin = body.origin_url.rstrip("/")
    success_url = f"{origin}/app/upgrade?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{origin}/app/upgrade"
    unit_amount = int(round(float(pkg["amount"]) * 100))
    metadata = {
        "user_id": user["id"],
        "plan": pkg["plan"],
        "interval": pkg["interval"],
        "package_id": body.package_id,
    }

    try:
        session = await asyncio.to_thread(
            stripe.checkout.Session.create,
            mode="subscription",
            customer=customer_id,
            client_reference_id=user["id"],
            line_items=[{
                "price_data": {
                    "currency": CURRENCY,
                    "unit_amount": unit_amount,
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
        )
    except stripe.error.StripeError as e:  # noqa
        logger.warning("[stripe checkout] error: %s", getattr(e, "user_message", e))
        raise HTTPException(status_code=502, detail="Stripe error creating checkout")

    await db.payment_transactions.insert_one({
        "id": str(uuid.uuid4()),
        "session_id": session.id,
        "user_id": user["id"],
        "email": user.get("email"),
        "amount": float(pkg["amount"]),
        "currency": CURRENCY,
        "plan": pkg["plan"],
        "interval": pkg["interval"],
        "package_id": body.package_id,
        "payment_status": "initiated",
        "status": "pending",
        "processed": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    return {"url": session.url, "session_id": session.id}


async def _apply_subscription_state(user_id: str, plan: str, sub: dict, session_id: str | None = None):
    """Idempotently sync the user's plan from a subscription object.

    ``trialing``/``active``/``past_due`` -> grant the plan.
    Terminal states (``canceled``/``unpaid``/``incomplete_expired``) -> none
    (never downgrade a superadmin).
    """
    if not user_id:
        return
    status = (sub or {}).get("status")
    updates = {
        "stripe_subscription_id": (sub or {}).get("id"),
        "subscription_status": status,
        "trial_ends_at": _ts_to_iso((sub or {}).get("trial_end")),
        "current_period_end": _ts_to_iso((sub or {}).get("current_period_end")),
    }
    user = await db.users.find_one({"id": user_id})
    if not user:
        return
    if status in _ACTIVE_SUB_STATES and plan in PLAN_RANK and plan != "none":
        updates["plan"] = plan
    elif status in ("canceled", "unpaid", "incomplete_expired"):
        if user.get("role") != "superadmin":
            updates["plan"] = "none"
    await db.users.update_one({"id": user_id}, {"$set": updates})

    # Audit record.
    await db.billing_subscriptions.update_one(
        {"stripe_subscription_id": updates["stripe_subscription_id"]},
        {"$set": {
            "user_id": user_id,
            "plan": plan,
            "status": status,
            "trial_ends_at": updates["trial_ends_at"],
            "current_period_end": updates["current_period_end"],
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }},
        upsert=True,
    )
    if session_id:
        await db.payment_transactions.update_one(
            {"session_id": session_id},
            {"$set": {
                "payment_status": "paid" if status in _ACTIVE_SUB_STATES else (status or "unknown"),
                "status": "complete" if status in _ACTIVE_SUB_STATES else "open",
                "subscription_status": status,
                "processed": status in _ACTIVE_SUB_STATES,
            }},
        )


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
        session = await asyncio.to_thread(stripe.checkout.Session.retrieve, session_id, expand=["subscription"])
    except stripe.error.StripeError as e:  # noqa
        logger.warning("[stripe sync] could not retrieve session %s: %s", session_id, e)
        return tx

    session_status = session.get("status")
    if session_status == "expired":
        await db.payment_transactions.update_one(
            {"id": tx["id"]},
            {"$set": {"payment_status": "expired", "status": "expired", "processed": False}},
        )
        return await db.payment_transactions.find_one({"id": tx["id"]}, {"_id": 0})

    sub = session.get("subscription")
    sub_dict = dict(sub) if sub else {}
    plan = (session.get("metadata") or {}).get("plan") or (sub_dict.get("metadata") or {}).get("plan")
    sub_status = sub_dict.get("status")
    active = (session_status == "complete") and (sub_status in _ACTIVE_SUB_STATES)
    user_id = session.get("client_reference_id") or (session.get("metadata") or {}).get("user_id")

    if active and plan and user_id:
        await _apply_subscription_state(user_id, plan, sub_dict, session_id=session_id)
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


async def refund_transaction_charge(tx: dict) -> dict:
    """Refund the underlying charge for a transaction's subscription.

    Recurring subscriptions don't have a single "the" charge tied to the
    checkout session itself — the actual money movement is the
    subscription's latest invoice, so that's what gets refunded.
    """
    _ensure_configured()
    session_id = tx.get("session_id")
    if not session_id:
        raise HTTPException(status_code=400, detail="Transaction has no Stripe session")
    try:
        session = await asyncio.to_thread(
            stripe.checkout.Session.retrieve, session_id,
            expand=["subscription.latest_invoice.payment_intent"],
        )
    except stripe.error.StripeError as e:  # noqa
        logger.warning("[stripe refund] session retrieve error: %s", getattr(e, "user_message", e))
        raise HTTPException(status_code=502, detail="Stripe error")

    sub = session.get("subscription")
    if not sub:
        raise HTTPException(status_code=400, detail="No subscription associated with this transaction")
    invoice = sub.get("latest_invoice")
    if not invoice:
        raise HTTPException(status_code=400, detail="No invoice found to refund")
    payment_intent = invoice.get("payment_intent")
    pi_id = payment_intent.get("id") if isinstance(payment_intent, dict) else payment_intent
    if not pi_id:
        raise HTTPException(status_code=400, detail="Nothing was charged yet (trial period) — nothing to refund")

    try:
        refund = await asyncio.to_thread(stripe.Refund.create, payment_intent=pi_id)
    except stripe.error.StripeError as e:  # noqa
        logger.warning("[stripe refund] error: %s", getattr(e, "user_message", e))
        raise HTTPException(status_code=502, detail=f"Stripe refund error: {getattr(e, 'user_message', str(e))}")

    await db.payment_transactions.update_one(
        {"id": tx["id"]},
        {"$set": {
            "refunded": True,
            "refund_id": refund.id,
            "refund_status": refund.status,
            "refunded_at": datetime.now(timezone.utc).isoformat(),
        }},
    )
    return {"ok": True, "refund_id": refund.id, "status": refund.status}


@router.get("/billing/status/{session_id}")
async def checkout_status(session_id: str, user: dict = Depends(get_current_user)):
    _ensure_configured()
    try:
        session = await asyncio.to_thread(
            stripe.checkout.Session.retrieve, session_id, expand=["subscription"]
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
    active = (session.get("status") == "complete") and (sub_status in _ACTIVE_SUB_STATES)

    if active and plan:
        await _apply_subscription_state(user["id"], plan, sub_dict, session_id=session_id)

    fresh = await db.users.find_one({"id": user["id"]}, {"_id": 0, "hashed_password": 0})
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

    if current.get("status") not in _ACTIVE_SUB_STATES:
        raise HTTPException(status_code=400, detail="Subscription is not active")

    item = current["items"]["data"][0]
    current_interval = ((item.get("price") or {}).get("recurring") or {}).get("interval")
    if (current.get("metadata") or {}).get("plan") == pkg["plan"] and current_interval == pkg["interval"]:
        raise HTTPException(status_code=400, detail="Already on this plan")

    unit_amount = int(round(float(pkg["amount"]) * 100))
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
    return_url = f"{body.origin_url.rstrip('/')}/app/settings"

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
    payload = await request.body()
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

    # Idempotency: skip already-processed events.
    if event_id:
        already = await db.stripe_events.find_one({"event_id": event_id})
        if already:
            return {"received": True, "duplicate": True}
        await db.stripe_events.insert_one({
            "event_id": event_id,
            "type": event_type,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })

    data_obj = (event.get("data") or {}).get("object") if isinstance(event, dict) else event.data.object
    data_obj = dict(data_obj) if data_obj else {}

    try:
        if event_type == "checkout.session.completed":
            sub_id = data_obj.get("subscription")
            user_id = data_obj.get("client_reference_id") or (data_obj.get("metadata") or {}).get("user_id")
            plan = (data_obj.get("metadata") or {}).get("plan")
            if sub_id:
                sub = await asyncio.to_thread(stripe.Subscription.retrieve, sub_id)
                plan = plan or (sub.get("metadata") or {}).get("plan")
                await _apply_subscription_state(user_id, plan, dict(sub), session_id=data_obj.get("id"))
        elif event_type in ("customer.subscription.updated", "customer.subscription.created",
                            "customer.subscription.deleted"):
            plan = (data_obj.get("metadata") or {}).get("plan")
            user_id = (data_obj.get("metadata") or {}).get("user_id")
            if not user_id:
                u = await db.users.find_one({"stripe_customer_id": data_obj.get("customer")})
                user_id = u.get("id") if u else None
            await _apply_subscription_state(user_id, plan, data_obj)
        elif event_type == "invoice.payment_failed":
            u = await db.users.find_one({"stripe_customer_id": data_obj.get("customer")})
            if u and u.get("role") != "superadmin":
                await db.users.update_one({"id": u["id"]}, {"$set": {"subscription_status": "past_due"}})
        elif event_type == "checkout.session.expired":
            # Customer opened checkout but abandoned it — resolve the
            # transaction to a terminal state instead of leaving it stuck at
            # "initiated" forever in the billing panel.
            await db.payment_transactions.update_one(
                {"session_id": data_obj.get("id")},
                {"$set": {"payment_status": "expired", "status": "expired", "processed": False}},
            )
    except Exception as e:  # noqa: BLE001
        logger.warning("[stripe webhook] handler error (%s): %s", event_type, e)

    return {"received": True}
