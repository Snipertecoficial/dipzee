"""Financial knowledge graph (L1).

A small directed graph linking macro factors and commodities → sectors →
companies, so an event on a factor/sector can be propagated to the *assets it
plausibly affects*, with a weight and a sign (direction of expected impact).

Scale note (YAGNI): at this size (hundreds of nodes/edges) a graph in Mongo +
an in-memory adjacency is more than enough. A dedicated graph DB (Neo4j) is a
documented future upgrade, not needed now.

Seeding:
- Curated domain edges (commodity/macro → sector) come from ``kg_seed`` — the
  real economic knowledge.
- Company → sector membership is read from the ``assets`` collection (authoritative
  sectors from the market-data providers), so it stays correct without a
  hand-maintained ticker map. LSE ``company_profiles`` can enrich this later.

Edges are stored in the INFLUENCE direction (src → dst): commodity/macro →
sector, sector → company. Propagation is then a simple forward walk from the
event's entity node down to companies.
"""
import logging
import time
from datetime import datetime, timezone

import kg_seed

logger = logging.getLogger(__name__)

DECAY = 0.85           # weight multiplier per hop
MIN_WEIGHT = 0.05      # prune paths below this
MAX_DEPTH = 4

# In-process cache of the loaded graph (rebuilt rarely; read a lot).
_CACHE_TTL = 600
_cache = {"graph": None, "at": 0.0}


def node_id(kind: str, key: str) -> str:
    return f"{kind}:{key}"


class Graph:
    """In-memory directed graph with weighted, signed edges."""

    def __init__(self):
        self.nodes: dict = {}          # id -> {id, kind, name, meta}
        self.adj: dict = {}            # id -> list[(dst_id, weight, sign)]

    def add_node(self, node_id_: str, kind: str, name: str = None, **meta) -> None:
        self.nodes[node_id_] = {"id": node_id_, "kind": kind, "name": name or node_id_, **meta}
        self.adj.setdefault(node_id_, [])

    def add_edge(self, src: str, dst: str, weight: float, sign: int = 1) -> None:
        self.adj.setdefault(src, []).append((dst, float(weight), 1 if sign >= 0 else -1))
        self.adj.setdefault(dst, [])

    def propagate(self, seeds, max_depth: int = MAX_DEPTH, decay: float = DECAY,
                  min_weight: float = MIN_WEIGHT) -> dict:
        """Forward-propagate influence from `seeds` (id or list of ids).

        Returns {node_id: {"weight": float in (0,1], "sign": +1/-1, "depth": int}}
        keeping, per node, the STRONGEST path found. Seeds start at weight 1.0.
        Weights only ever decay along a path, so re-expanding on a strictly
        stronger path (a node with multiple parents) is bounded and terminates;
        the influence direction is acyclic, so there are no true loops anyway.
        """
        if isinstance(seeds, str):
            seeds = [seeds]
        best: dict = {}
        frontier = [(s, 1.0, 1, 0) for s in seeds if s in self.nodes or s in self.adj]
        while frontier:
            node, w, sign, depth = frontier.pop()
            prev = best.get(node)
            if prev is not None and w <= prev["weight"] + 1e-9:
                continue  # already reached this node by an equal/stronger path
            best[node] = {"weight": w, "sign": sign, "depth": depth}
            if depth >= max_depth:
                continue
            for dst, ew, es in self.adj.get(node, []):
                nw = w * ew * decay
                if nw >= min_weight:
                    frontier.append((dst, nw, sign * es, depth + 1))
        return best

    def affected_companies(self, seeds, **kw) -> list:
        """Propagate, then return only company nodes, strongest first."""
        reached = self.propagate(seeds, **kw)
        out = []
        for nid, info in reached.items():
            node = self.nodes.get(nid)
            if node and node.get("kind") == "company" and nid not in _as_set(seeds):
                out.append({
                    "id": nid, "symbol": node.get("symbol") or nid.split(":", 1)[-1],
                    "name": node.get("name"), "sector": node.get("sector"),
                    "weight": round(info["weight"], 4), "sign": info["sign"], "depth": info["depth"],
                })
        out.sort(key=lambda x: x["weight"], reverse=True)
        return out


def _as_set(seeds):
    return {seeds} if isinstance(seeds, str) else set(seeds)


def build_graph(companies: list) -> Graph:
    """Build a Graph from curated seed data + a list of {ticker, sector} companies.
    Pure (no DB) so it's unit-testable."""
    g = Graph()
    # Sectors
    for sector, display in kg_seed.SECTORS.items():
        g.add_node(node_id("sector", sector), "sector", display, sector=sector)
    # Commodities -> sectors
    for cid, spec in kg_seed.COMMODITY_EXPOSURE.items():
        g.add_node(node_id("commodity", cid), "commodity", spec["name"])
        for sector, weight in spec["sectors"].items():
            sid = node_id("sector", sector)
            if sid in g.nodes:
                g.add_edge(node_id("commodity", cid), sid, abs(weight), 1 if weight >= 0 else -1)
    # Macro -> sectors
    for mid, spec in kg_seed.MACRO_SENSITIVITY.items():
        g.add_node(node_id("macro", mid), "macro", spec["name"])
        for sector, (weight, sign) in spec["sectors"].items():
            sid = node_id("sector", sector)
            if sid in g.nodes:
                g.add_edge(node_id("macro", mid), sid, abs(weight), sign)
    # Companies -> membership edge sector -> company (influence flows down)
    for c in companies:
        ticker = (c.get("ticker") or "").strip().upper()
        if not ticker:
            continue
        sector = kg_seed.normalize_sector(c.get("sector"))
        cid = node_id("company", ticker)
        g.add_node(cid, "company", c.get("name") or ticker, symbol=ticker, sector=sector)
        if sector:
            sid = node_id("sector", sector)
            if sid in g.nodes:
                g.add_edge(sid, cid, 1.0, 1)
    return g


# --------------------------------------------------------------------------- #
# DB-backed seeding + loading
# --------------------------------------------------------------------------- #
async def rebuild_graph(db) -> dict:
    """Rebuild the graph from curated seed + the assets collection and persist
    it to kg_nodes/kg_edges (idempotent upserts). Returns counts."""
    companies = []
    async for a in db.assets.find({}, {"_id": 0, "ticker": 1, "name": 1, "sector": 1}):
        if a.get("ticker"):
            companies.append(a)
    g = build_graph(companies)

    now = datetime.now(timezone.utc).isoformat()
    for nid, node in g.nodes.items():
        await db.kg_nodes.update_one({"id": nid}, {"$set": {**node, "updated_at": now}}, upsert=True)
    # Edges: replace wholesale (cheap, keeps the store consistent with the seed).
    await db.kg_edges.delete_many({})
    edges = []
    for src, lst in g.adj.items():
        for dst, weight, sign in lst:
            edges.append({"src": src, "dst": dst, "weight": weight, "sign": sign})
    if edges:
        await db.kg_edges.insert_many(edges)

    _cache["graph"] = g
    _cache["at"] = time.time()
    logger.info("[kg] rebuilt: %d nodes, %d edges, %d companies", len(g.nodes), len(edges), len(companies))
    return {"nodes": len(g.nodes), "edges": len(edges), "companies": len(companies)}


async def load_graph(db, force: bool = False) -> Graph:
    """Load the graph into memory (cached). Seeds from curated data + assets if
    the store is empty."""
    now = time.time()
    if not force and _cache["graph"] is not None and now - _cache["at"] < _CACHE_TTL:
        return _cache["graph"]

    g = Graph()
    node_count = 0
    async for n in db.kg_nodes.find({}, {"_id": 0}):
        nid = n.get("id")
        if not nid:
            continue
        g.nodes[nid] = n
        g.adj.setdefault(nid, [])
        node_count += 1
    if node_count == 0:
        # Empty store -> seed it now.
        await rebuild_graph(db)
        return _cache["graph"]
    async for e in db.kg_edges.find({}, {"_id": 0}):
        if e.get("src") and e.get("dst"):
            g.add_edge(e["src"], e["dst"], e.get("weight", 1.0), e.get("sign", 1))

    _cache["graph"] = g
    _cache["at"] = now
    return g


async def affected_assets(db, seeds, **kw) -> list:
    """Convenience: load the graph and return companies affected by `seeds`."""
    g = await load_graph(db)
    return g.affected_companies(seeds, **kw)


async def graph_status(db) -> dict:
    nodes = await db.kg_nodes.count_documents({})
    edges = await db.kg_edges.count_documents({})
    by_kind = {}
    for kind in ("company", "sector", "commodity", "macro"):
        by_kind[kind] = await db.kg_nodes.count_documents({"kind": kind})
    return {"nodes": nodes, "edges": edges, "by_kind": by_kind}
