"""Market memory (L4): embed events, retrieve similar past situations, learn outcomes.

Answers "the last few times this kind of thing happened, what did the affected
assets do next?" — e.g. *when crude oil jumped, energy names rose ~X% over the
following week*.

Design (YAGNI): events are embedded with a DETERMINISTIC structured vector (no
external embedding model, no cost) — factor moves + sentiment + event type + net
sector impact. Similarity is brute-force cosine over the in-memory set (N is
small). A dedicated vector DB is a documented future upgrade, not needed now.

Outcomes are computed from stored ``lse_candles`` when available: the forward
return of the event's affected symbols over a horizon. With no price history the
outcome stays "pending" and the event still contributes to similarity — the
summary just reports fewer resolved outcomes.
"""
import logging
import math
from datetime import datetime, timezone

import kg_seed
from event_service import _COMMODITY_KEYWORDS, _MACRO_KEYWORDS, EVENT_TYPES

logger = logging.getLogger(__name__)

DEFAULT_HORIZON_DAYS = 5

# Fixed, ordered vector layout (stable so stored vectors stay comparable).
_FACTORS = list(_COMMODITY_KEYWORDS) + list(_MACRO_KEYWORDS)   # 5 + 4 = 9
_SECTORS = list(kg_seed.SECTORS)                                # 11
_EVENT_TYPES = sorted(EVENT_TYPES)                              # 11
VECTOR_DIM = len(_FACTORS) + 1 + len(_EVENT_TYPES) + len(_SECTORS)

_MOVE = {"up": 1.0, "down": -1.0, "unclear": 0.0}


def event_vector(event: dict) -> list:
    """Deterministic structured embedding of an enriched event. Pure."""
    vec = [0.0] * VECTOR_DIM
    ent = event.get("entities", {}) or {}
    factor_moves = {}
    for f in (ent.get("commodities", []) + ent.get("macro", [])):
        if f.get("id"):
            factor_moves[f["id"]] = _MOVE.get(f.get("move"), 0.0)
    i = 0
    for fid in _FACTORS:
        vec[i] = factor_moves.get(fid, 0.0)
        i += 1
    # sentiment
    try:
        vec[i] = max(-1.0, min(1.0, float(event.get("sentiment") or 0.0)))
    except (TypeError, ValueError):
        vec[i] = 0.0
    i += 1
    # event type one-hot
    et = event.get("event_type", "other")
    for j, t in enumerate(_EVENT_TYPES):
        vec[i + j] = 1.0 if t == et else 0.0
    i += len(_EVENT_TYPES)
    # net signed impact per sector
    sector_impact = {s: 0.0 for s in _SECTORS}
    for a in event.get("affected", []):
        sec = a.get("sector")
        if sec in sector_impact:
            try:
                sector_impact[sec] += float(a.get("impact") or 0.0)
            except (TypeError, ValueError):
                pass
    for j, s in enumerate(_SECTORS):
        vec[i + j] = max(-1.0, min(1.0, sector_impact[s]))
    return vec


def cosine(a: list, b: list) -> float:
    """Cosine similarity in [-1, 1]; 0 when either vector is all-zero."""
    dot = na = nb = 0.0
    for x, y in zip(a, b):
        dot += x * y
        na += x * x
        nb += y * y
    if na == 0 or nb == 0:
        return 0.0
    return dot / (math.sqrt(na) * math.sqrt(nb))


def knn(query_vec: list, candidates: list, k: int = 5, min_sim: float = 0.1) -> list:
    """Brute-force k nearest by cosine. `candidates` is a list of dicts each with
    a 'vector'. Returns the top-k (excluding self by id) with a 'similarity'."""
    scored = []
    for c in candidates:
        vec = c.get("vector")
        if not vec:
            continue
        sim = cosine(query_vec, vec)
        if sim >= min_sim:
            scored.append({**c, "similarity": round(sim, 4)})
    scored.sort(key=lambda x: x["similarity"], reverse=True)
    return scored[:k]


def _event_date(event: dict):
    """Best-effort event date (date only) from datetime/enriched_at."""
    raw = event.get("datetime") or event.get("enriched_at")
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        ts = raw / 1000.0 if raw > 1e12 else float(raw)
        try:
            return datetime.fromtimestamp(ts, tz=timezone.utc).date().isoformat()
        except (ValueError, OverflowError, OSError):
            return None
    s = str(raw)
    return s[:10] if len(s) >= 10 else None


async def _forward_return(db, symbol: str, from_date: str, horizon: int) -> float:
    """Forward return of `symbol` over `horizon` trading days on/after from_date,
    from lse_candles. None when there isn't enough history."""
    if not from_date:
        return None
    rows = await db.lse_candles.find(
        {"symbol": symbol, "timeframe": "1d", "ts": {"$gte": from_date}}, {"_id": 0, "ts": 1, "close": 1}
    ).sort("ts", 1).to_list(horizon + 5)
    closes = [r.get("close") for r in rows if r.get("close") is not None]
    if len(closes) <= horizon:
        return None
    try:
        start, end = float(closes[0]), float(closes[horizon])
        if start == 0:
            return None
        return round((end - start) / start * 100.0, 3)
    except (TypeError, ValueError):
        return None


async def compute_outcome(db, event: dict, horizon: int = DEFAULT_HORIZON_DAYS) -> dict:
    """Impact-weighted average forward return of the event's affected symbols.
    Returns {status, horizon_days, avg_return, resolved, per_symbol}."""
    date = _event_date(event)
    affected = sorted(event.get("affected", []), key=lambda a: abs(a.get("impact") or 0), reverse=True)[:8]
    num = den = 0.0
    per_symbol = []
    resolved = 0
    for a in affected:
        sym = a.get("symbol")
        ret = await _forward_return(db, sym, date, horizon)
        per_symbol.append({"symbol": sym, "return_pct": ret})
        if ret is not None:
            w = abs(float(a.get("impact") or 0.0)) or 0.1
            num += ret * w
            den += w
            resolved += 1
    status = "resolved" if resolved else "pending"
    return {
        "status": status,
        "horizon_days": horizon,
        "avg_return": round(num / den, 3) if den else None,
        "resolved": resolved,
        "per_symbol": per_symbol,
    }


async def index_events(db, horizon: int = DEFAULT_HORIZON_DAYS, limit: int = 500) -> dict:
    """Backfill event_memory from market_events: compute vector + outcome for
    events not yet indexed (or still pending an outcome). Deterministic, no LLM."""
    processed = resolved = 0
    events = await db.market_events.find({}, {"_id": 0}).sort("enriched_at", -1).to_list(limit)
    for event in events:
        eid = event.get("id")
        if not eid:
            continue
        existing = await db.event_memory.find_one({"id": eid}, {"outcome.status": 1})
        if existing and (existing.get("outcome") or {}).get("status") == "resolved":
            continue  # already fully resolved
        vec = event_vector(event)
        outcome = await compute_outcome(db, event, horizon)
        doc = {
            "id": eid,
            "vector": vec,
            "event_date": _event_date(event),
            "headline": event.get("headline"),
            "event_type": event.get("event_type"),
            "entities": event.get("entities"),
            "affected_symbols": [a.get("symbol") for a in event.get("affected", [])][:8],
            "outcome": outcome,
            "indexed_at": datetime.now(timezone.utc).isoformat(),
        }
        await db.event_memory.update_one({"id": eid}, {"$set": doc}, upsert=True)
        processed += 1
        if outcome["status"] == "resolved":
            resolved += 1
    return {"processed": processed, "resolved": resolved, "scanned": len(events)}


async def similar_situations(db, query_event: dict, k: int = 5) -> dict:
    """Find past events similar to `query_event` and summarize their outcomes.
    Deterministic (no LLM): 'in N similar past situations, affected assets moved
    on average X% over H days'."""
    qvec = event_vector(query_event)
    candidates = await db.event_memory.find(
        {"id": {"$ne": query_event.get("id")}}, {"_id": 0}
    ).to_list(2000)
    neighbors = knn(qvec, candidates, k=k)

    returns = [n["outcome"]["avg_return"] for n in neighbors
               if n.get("outcome", {}).get("avg_return") is not None]
    summary = {
        "matches": len(neighbors),
        "resolved": len(returns),
        "avg_return": round(sum(returns) / len(returns), 3) if returns else None,
        "horizon_days": neighbors[0]["outcome"]["horizon_days"] if neighbors else DEFAULT_HORIZON_DAYS,
        "positive_share": round(sum(1 for r in returns if r > 0) / len(returns), 3) if returns else None,
    }
    return {
        "summary": summary,
        "neighbors": [{
            "id": n["id"], "headline": n.get("headline"), "similarity": n["similarity"],
            "event_date": n.get("event_date"),
            "avg_return": n.get("outcome", {}).get("avg_return"),
        } for n in neighbors],
    }


async def memory_status(db) -> dict:
    total = await db.event_memory.count_documents({})
    resolved = await db.event_memory.count_documents({"outcome.status": "resolved"})
    return {"indexed": total, "resolved": resolved, "vector_dim": VECTOR_DIM}
