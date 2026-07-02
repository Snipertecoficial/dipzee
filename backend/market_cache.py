"""Resilient caching layer for market data.

Strategy for a "never fails for clients" experience on top of a rate-limited,
best-effort upstream (Yahoo via yfinance):

1. In-memory TTL cache (fast path, per-process).
2. On miss -> call the loader with exponential-backoff retries.
3. On success -> refresh memory AND persist to MongoDB (durable snapshot).
4. On failure (rate-limit / timeout / empty) -> serve the last-known-good value
   from memory or MongoDB, flagged as `stale=True`. Only when there is NO cached
   value at all do we surface an error to the caller.

This means transient Yahoo failures are invisible to end users: they always get
the most recent good data instead of a 5xx.
"""
import asyncio
import datetime as _dt
import logging
import math
import time
from datetime import datetime, timezone

from database import db

logger = logging.getLogger(__name__)

# key -> {"exp": float, "payload": Any, "fetched_at": iso}
_MEM: dict = {}


def json_safe(obj):
    """Recursively convert a payload into JSON/Mongo-serializable primitives.

    Handles datetimes/timezones, numpy scalars, NaN/Inf and unknown objects
    (stringified as a last resort) so upstream data never breaks serialization.
    """
    if obj is None or isinstance(obj, (str, int, bool)):
        return obj
    if isinstance(obj, float):
        return None if (math.isnan(obj) or math.isinf(obj)) else obj
    if isinstance(obj, dict):
        return {str(k): json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [json_safe(v) for v in obj]
    if isinstance(obj, (_dt.datetime, _dt.date)):
        try:
            return obj.isoformat()
        except Exception:  # noqa: BLE001
            return str(obj)
    if isinstance(obj, _dt.tzinfo):
        return str(obj)
    if hasattr(obj, "item"):  # numpy scalar
        try:
            return json_safe(obj.item())
        except Exception:  # noqa: BLE001
            return str(obj)
    try:
        import json as _json
        _json.dumps(obj)
        return obj
    except Exception:  # noqa: BLE001
        return str(obj)


def retry(fn, tries: int = 3, base_delay: float = 0.6):
    """Call a blocking fn with exponential backoff. Re-raises the last error."""
    last = None
    for attempt in range(tries):
        try:
            return fn()
        except Exception as e:  # noqa: BLE001 - upstream can raise anything
            last = e
            logger.warning("market loader failed (%s) attempt %d/%d: %s",
                           type(e).__name__, attempt + 1, tries, e)
            if attempt < tries - 1:
                time.sleep(base_delay * (2 ** attempt))
    raise last if last else RuntimeError("unknown loader error")


async def _persist(key: str, payload):
    try:
        await db.market_cache.update_one(
            {"_id": key},
            {"$set": {"payload": payload, "fetched_at": datetime.now(timezone.utc).isoformat()}},
            upsert=True,
        )
    except Exception as e:  # noqa: BLE001
        logger.warning("market_cache persist failed for %s: %s", key, e)


async def _load_persisted(key: str):
    try:
        doc = await db.market_cache.find_one({"_id": key})
        if doc:
            return doc.get("payload"), doc.get("fetched_at")
    except Exception as e:  # noqa: BLE001
        logger.warning("market_cache read failed for %s: %s", key, e)
    return None, None


async def cached(key: str, ttl: int, loader, tries: int = 3):
    """Return an envelope dict or None (only when no data exists anywhere).

    Envelope: {"data": <payload>, "cached": bool, "stale": bool, "fetched_at": iso}
    `loader` is a *blocking* callable executed in a worker thread. It must return
    a non-None payload on success (empty list/dict is considered valid).
    """
    now = time.time()
    hit = _MEM.get(key)
    if hit and hit["exp"] > now:
        return {"data": hit["payload"], "cached": True, "stale": False, "fetched_at": hit["fetched_at"]}

    try:
        payload = await asyncio.to_thread(retry, loader, tries)
        if payload is None:
            raise ValueError("empty payload")
        payload = json_safe(payload)
        fetched_at = datetime.now(timezone.utc).isoformat()
        _MEM[key] = {"exp": now + ttl, "payload": payload, "fetched_at": fetched_at}
        await _persist(key, payload)
        return {"data": payload, "cached": False, "stale": False, "fetched_at": fetched_at}
    except Exception as e:  # noqa: BLE001
        logger.warning("market fetch failed for %s -> serving stale if available: %s", key, e)
        # Stale fallback: expired memory value first, then durable Mongo snapshot.
        if hit:
            return {"data": hit["payload"], "cached": True, "stale": True, "fetched_at": hit["fetched_at"]}
        payload, fetched_at = await _load_persisted(key)
        if payload is not None:
            # Warm memory with a short TTL so we do not hammer upstream while stale.
            _MEM[key] = {"exp": now + min(ttl, 30), "payload": payload, "fetched_at": fetched_at}
            return {"data": payload, "cached": True, "stale": True, "fetched_at": fetched_at}
        return None


def invalidate(key: str):
    _MEM.pop(key, None)
