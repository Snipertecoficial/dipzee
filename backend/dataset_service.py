"""Proprietary dataset + inference logging (L5).

Every model inference (the deterministic context we fed in + the output we
produced) and every anonymized user decision is logged, building the moat
dataset over time — training models on our own data is permitted by the LSE
terms. This is *analysis we generated*, not raw LSE redistribution.

Privacy (LGPD) by construction:
- No PII is ever stored here — no email, name, or IP. A user is referenced only
  by a salted, one-way pseudonym (``anon_subject``), so records can be grouped
  per user for learning without identifying anyone, and a user's records can
  still be purged on request (right to erasure) via their pseudonym.
- Retention is bounded (``DATASET_RETENTION_DAYS``); a daily job prunes older
  rows. Logging is always best-effort and never blocks or breaks a request.
"""
import hashlib
import logging
import os
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)

RETENTION_DAYS = int(os.environ.get("DATASET_RETENTION_DAYS", "540"))  # ~18 months


def _salt() -> str:
    # Dedicated salt if provided, else reuse the JWT secret so the pseudonym is
    # stable and non-reversible without server secrets.
    value = os.environ.get("DATASET_SALT") or os.environ.get("JWT_SECRET")
    if not value and os.environ.get("ENV") == "production":
        raise RuntimeError("DATASET_SALT is required in production")
    return value or "dipzee-dataset-dev-only"


def anon_subject(user_id: str) -> str:
    """One-way salted pseudonym for a user id (no PII, stable per user)."""
    if not user_id:
        return "anon"
    return "u_" + hashlib.sha256(f"{_salt()}:{user_id}".encode("utf-8")).hexdigest()[:16]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def log_inference(db, kind: str, subject: str, context: dict, output: dict,
                        model: str = None, user: dict = None) -> None:
    """Record one (context -> output) training pair. Best-effort; never raises.

    `context` is the deterministic input we composed (score, net impact, factors,
    ...); `output` is the model result. Together they're a supervised example."""
    try:
        doc = {
            "ts": _now(),
            "kind": kind,                       # e.g. "intel_asset", "intel_macro", "ai_analyst"
            "subject": (subject or "").upper() or None,
            "context": context,
            "output": output,
            "model": model,
            "plan": (user or {}).get("plan"),
            "locale": (user or {}).get("locale"),
            "anon": anon_subject((user or {}).get("id")) if user else None,
        }
        await db.inference_log.insert_one(doc)
    except Exception as e:  # noqa: BLE001 - logging must never break the request
        logger.warning("[dataset] log_inference failed: %s", e)


async def log_decision(db, action: str, ticker: str, user: dict = None, meta: dict = None) -> None:
    """Record an anonymized user decision/interest signal (add-to-watchlist,
    alert-created, intel-viewed, ...). Best-effort; never raises."""
    try:
        doc = {
            "ts": _now(),
            "action": action,
            "subject": (ticker or "").upper() or None,
            "plan": (user or {}).get("plan"),
            "anon": anon_subject((user or {}).get("id")) if user else None,
            "meta": meta or {},
        }
        await db.decision_log.insert_one(doc)
    except Exception as e:  # noqa: BLE001
        logger.warning("[dataset] log_decision failed: %s", e)


async def prune_old(db, retention_days: int = None) -> dict:
    """Delete rows older than the retention window. Returns counts removed."""
    days = retention_days if retention_days is not None else RETENTION_DAYS
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    removed = {}
    for coll in ("inference_log", "decision_log"):
        res = await db[coll].delete_many({"ts": {"$lt": cutoff}})
        removed[coll] = getattr(res, "deleted_count", 0)
    return {"cutoff": cutoff, "removed": removed}


async def purge_user(db, user_id: str) -> dict:
    """Right-to-erasure: remove a user's pseudonymous records across the dataset."""
    anon = anon_subject(user_id)
    removed = {}
    for coll in ("inference_log", "decision_log"):
        res = await db[coll].delete_many({"anon": anon})
        removed[coll] = getattr(res, "deleted_count", 0)
    return {"anon": anon, "removed": removed}


async def dataset_status(db) -> dict:
    """Counts + retention for the admin panel."""
    return {
        "inferences": await db.inference_log.count_documents({}),
        "decisions": await db.decision_log.count_documents({}),
        "retention_days": RETENTION_DAYS,
        "by_kind": {
            k: await db.inference_log.count_documents({"kind": k})
            for k in ("intel_asset", "intel_macro", "ai_analyst")
        },
    }
