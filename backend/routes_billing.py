"""Stripe subscription billing (Checkout + status polling + webhook).

Uses the emergentintegrations StripeCheckout helper. Amounts are defined
SERVER-SIDE only (never trusted from the client) to prevent price manipulation.
On successful payment the user's plan is upgraded (idempotently).
"""
import logging
import os
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from database import db
from security import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(tags=["billing"])

# Server-side price packages in CAD (annual = ~20% off 12 months).
PACKAGES = {
    "pro_monthly": {"amount": 12.99, "plan": "pro", "billing": "monthly"},
    "pro_annual": {"amount": 124.70, "plan": "pro", "billing": "annual"},
    "investor_monthly": {"amount": 24.99, "plan": "investor", "billing": "monthly"},
    "investor_annual": {"amount": 239.90, "plan": "investor", "billing": "annual"},
}
CURRENCY = "cad"


def _get_checkout(request: Request):
    api_key = os.environ.get("STRIPE_API_KEY")
    if not api_key:
        raise HTTPException(status_code=503, detail="Billing not configured")
    from emergentintegrations.payments.stripe.checkout import StripeCheckout
    host_url = str(request.base_url)
    webhook_url = f"{host_url}api/webhook/stripe"
    return StripeCheckout(api_key=api_key, webhook_url=webhook_url)


class CheckoutIn(BaseModel):
    package_id: str
    origin_url: str


@router.get("/billing/config")
async def billing_config():
    return {"configured": bool(os.environ.get("STRIPE_API_KEY")), "packages": PACKAGES, "currency": CURRENCY.upper()}


@router.post("/billing/checkout")
async def create_checkout(body: CheckoutIn, request: Request, user: dict = Depends(get_current_user)):
    pkg = PACKAGES.get(body.package_id)
    if not pkg:
        raise HTTPException(status_code=400, detail="Invalid package")
    from emergentintegrations.payments.stripe.checkout import CheckoutSessionRequest
    stripe_checkout = _get_checkout(request)
    origin = body.origin_url.rstrip("/")
    success_url = f"{origin}/app/upgrade?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{origin}/app/upgrade"
    metadata = {"user_id": user["id"], "plan": pkg["plan"], "billing": pkg["billing"], "package_id": body.package_id}
    req = CheckoutSessionRequest(amount=float(pkg["amount"]), currency=CURRENCY, success_url=success_url, cancel_url=cancel_url, metadata=metadata)
    session = await stripe_checkout.create_checkout_session(req)

    await db.payment_transactions.insert_one({
        "id": str(uuid.uuid4()),
        "session_id": session.session_id,
        "user_id": user["id"],
        "email": user.get("email"),
        "amount": float(pkg["amount"]),
        "currency": CURRENCY,
        "plan": pkg["plan"],
        "billing": pkg["billing"],
        "payment_status": "initiated",
        "status": "pending",
        "processed": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    return {"url": session.url, "session_id": session.session_id}


async def _apply_paid(session_id: str, metadata: dict):
    """Idempotently mark transaction paid and upgrade the user's plan."""
    tx = await db.payment_transactions.find_one({"session_id": session_id})
    if not tx or tx.get("processed"):
        return
    plan = (metadata or {}).get("plan") or tx.get("plan")
    user_id = (metadata or {}).get("user_id") or tx.get("user_id")
    await db.payment_transactions.update_one(
        {"session_id": session_id},
        {"$set": {"payment_status": "paid", "status": "complete", "processed": True}},
    )
    if plan and user_id:
        await db.users.update_one({"id": user_id}, {"$set": {"plan": plan}})


@router.get("/billing/status/{session_id}")
async def checkout_status(session_id: str, request: Request, user: dict = Depends(get_current_user)):
    stripe_checkout = _get_checkout(request)
    status = await stripe_checkout.get_checkout_status(session_id)
    if status.payment_status == "paid":
        await _apply_paid(session_id, status.metadata)
    else:
        await db.payment_transactions.update_one(
            {"session_id": session_id},
            {"$set": {"payment_status": status.payment_status, "status": status.status}},
        )
    fresh_user = await db.users.find_one({"id": user["id"]}, {"_id": 0, "hashed_password": 0})
    return {"payment_status": status.payment_status, "status": status.status, "plan": fresh_user.get("plan")}


@router.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    body = await request.body()
    sig = request.headers.get("Stripe-Signature")
    try:
        stripe_checkout = _get_checkout(request)
        event = await stripe_checkout.handle_webhook(body, sig)
    except Exception as e:  # noqa: BLE001
        logger.warning("[stripe webhook] error: %s", e)
        raise HTTPException(status_code=400, detail="Invalid webhook")
    if event.payment_status == "paid" and event.session_id:
        await _apply_paid(event.session_id, event.metadata or {})
    return {"received": True}
