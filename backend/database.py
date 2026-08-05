"""Shared MongoDB connection for Dipzee."""
import os
from pathlib import Path
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import OperationFailure

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]


# MongoDB error codes for "an index with these keys already exists, but with
# different options" — e.g. a legacy non-unique index versus a now-unique
# declaration. Names are auto-generated from the keys, so the two collide.
_INDEX_OPTION_CONFLICT_CODES = (85, 86)  # IndexOptionsConflict / IndexKeySpecsConflict


async def _create_index(coll, keys, **opts):
    """Create an index, self-healing when only its OPTIONS changed.

    ``create_index`` is a no-op for an identical spec, but it raises when an index
    with the same keys already exists with *different* options (adding ``unique``,
    switching ``sparse`` to a ``partialFilterExpression``, changing a TTL, ...).
    Left unhandled that aborts the deploy preflight (``scripts/preflight_schema``)
    and blocks the release even though the fix is mechanical. Here we converge to
    the declared spec: drop the conflicting same-key index and recreate it with
    the options the code asks for. Any *other* failure still propagates, so index
    creation remains a genuine readiness gate (see ``ensure_indexes`` docstring).
    """
    try:
        return await coll.create_index(keys, **opts)
    except OperationFailure as exc:
        if exc.code not in _INDEX_OPTION_CONFLICT_CODES:
            raise
        target = [(keys, 1)] if isinstance(keys, str) else list(keys)
        for name, spec in (await coll.index_information()).items():
            if name != '_id_' and spec.get('key') == target:
                await coll.drop_index(name)
                break
        return await coll.create_index(keys, **opts)


async def ensure_indexes():
    """Create correctness, tenancy, expiry and query indexes.

    Index creation is part of readiness: callers intentionally let failures
    abort startup instead of serving without uniqueness/security invariants.
    Each declaration goes through ``_create_index`` so a pre-existing index whose
    options changed is reconciled in place instead of aborting the whole run.
    """
    await _create_index(db.users, 'email', unique=True)
    await _create_index(db.users, 'id', unique=True)
    # A sparse unique index still indexes explicit ``null`` values. Most users
    # legitimately have no Stripe customer yet, so enforce uniqueness only for
    # actual string identifiers and exclude their ``null`` placeholders.
    await _create_index(
        db.users,
        'stripe_customer_id',
        unique=True,
        partialFilterExpression={'stripe_customer_id': {'$type': 'string'}},
    )
    await _create_index(db.assets, 'ticker', unique=True)
    await _create_index(db.assets, [('score', -1), ('ticker', 1)])
    await _create_index(db.watchlist_items, 'user_id')
    await _create_index(db.watchlist_items, 'id', unique=True)
    await _create_index(db.watchlist_items, [('user_id', 1), ('ticker', 1)], unique=True)
    await _create_index(db.alerts, 'user_id')
    await _create_index(db.alerts, 'id', unique=True)
    await _create_index(db.alerts, 'ticker')
    await _create_index(db.alerts, [('ticker', 1), ('active', 1)])
    await _create_index(db.alert_events, 'user_id')
    await _create_index(db.alert_events, 'id', unique=True)
    await _create_index(db.alert_events, 'dedupe_key', unique=True, sparse=True)
    await _create_index(db.alert_events, [('user_id', 1), ('hidden', 1), ('read', 1), ('created_at', -1)])
    await _create_index(db.positions, 'id', unique=True)
    await _create_index(db.positions, [('user_id', 1), ('ticker', 1)], unique=True)
    await _create_index(db.password_resets, 'user_id', unique=True)
    await _create_index(db.password_resets, 'token_hash', unique=True)
    await _create_index(db.password_resets, 'purge_at', expireAfterSeconds=0)
    await _create_index(db.refresh_tokens, 'id', unique=True)
    await _create_index(db.refresh_tokens, 'token_hash', unique=True)
    await _create_index(db.refresh_tokens, 'user_id')
    await _create_index(db.refresh_tokens, [('user_id', 1), ('family_id', 1), ('revoked', 1)])
    await _create_index(db.refresh_tokens, 'purge_at', expireAfterSeconds=0)
    await _create_index(db.login_attempts, 'purge_at', expireAfterSeconds=0)
    await _create_index(db.user_operation_locks, 'expires_at', expireAfterSeconds=0)
    # Billing: unique event_id enforces webhook idempotency even under a
    # concurrent double-delivery race; unique session_id keys every reconcile/
    # poll/webhook lookup and prevents duplicate transaction rows.
    await _create_index(db.stripe_events, 'event_id', unique=True)
    await _create_index(db.stripe_events, 'purge_at', expireAfterSeconds=0)
    await _create_index(db.payment_transactions, 'id', unique=True)
    await _create_index(db.payment_transactions, 'session_id', unique=True, sparse=True, name='session_id_sparse_unique')
    await _create_index(db.payment_transactions, [('user_id', 1), ('created_at', -1)])
    await _create_index(db.payment_transactions, [('processed', 1), ('created_at', 1)])
    await _create_index(db.billing_subscriptions, 'stripe_subscription_id', unique=True)
    await _create_index(db.billing_subscriptions, 'user_id')
    await _create_index(db.billing_subscription_events, 'event_id', unique=True)
    await _create_index(db.billing_operation_locks, 'expires_at', expireAfterSeconds=0)
    await _create_index(db.billing_outbox, 'operation_id', unique=True)
    await _create_index(db.billing_outbox, [('status', 1), ('next_attempt_at', 1)])

    await _create_index(db.app_settings, 'id', unique=True)
    await _create_index(db.announcements, 'id', unique=True)
    await _create_index(db.announcements, [('active', 1), ('created_at', -1)])
    await _create_index(db.partner_ads, 'id', unique=True)
    await _create_index(db.partner_ads, [('active', 1), ('placement', 1)])
    await _create_index(db.ai_analyses, [('ticker', 1), ('locale', 1)], unique=True)
    await _create_index(db.admin_audit_log, 'id', unique=True)
    await _create_index(db.admin_audit_log, [('admin_id', 1), ('created_at', -1)])
    await _create_index(db.admin_audit_log, 'purge_at', expireAfterSeconds=0)

    # LSE intelligence layer. Normalized, point-in-time correct: the unique
    # composite keys let re-ingestion of the same period upsert in place rather
    # than duplicate rows. Only the tracked universe is stored, never the full
    # catalog, so these stay small.
    await _create_index(db.lse_candles, [('symbol', 1), ('timeframe', 1), ('ts', 1)], unique=True)
    await _create_index(db.lse_candles, [('symbol', 1), ('timeframe', 1), ('ts', -1)])
    await _create_index(db.lse_fundamentals, 'symbol', unique=True)
    await _create_index(db.lse_dividends, [('symbol', 1), ('ex_date', 1)], unique=True)
    await _create_index(db.lse_splits, [('symbol', 1), ('date', 1)], unique=True)
    await _create_index(db.lse_options_flow, [('symbol', 1), ('ts', -1)])
    await _create_index(db.lse_macro_series, [('series', 1), ('date', 1)], unique=True)
    await _create_index(db.lse_econ_calendar, [('region', 1), ('date', 1)])
    await _create_index(db.lse_insider, [('symbol', 1), ('date', -1)])
    await _create_index(db.lse_ingest_log, [('at', -1)])

    # Knowledge graph (L1): nodes keyed by id, edges by src for fast fan-out.
    await _create_index(db.kg_nodes, 'id', unique=True)
    await _create_index(db.kg_nodes, 'kind')
    await _create_index(db.kg_edges, 'src')
    await _create_index(db.kg_edges, [('src', 1), ('dst', 1)])

    # Market events (L2): unique content id (dedup), lookup by affected asset,
    # recency ordering.
    await _create_index(db.market_events, 'id', unique=True)
    await _create_index(db.market_events, 'affected.symbol')
    await _create_index(db.market_events, [('enriched_at', -1)])

    # Intelligence insight caches (L3), keyed like ai_analyses.
    await _create_index(db.intel_insights, [('ticker', 1), ('locale', 1)], unique=True)
    await _create_index(db.intel_macro, [('id', 1), ('locale', 1)], unique=True)

    # Market memory (L4): event embeddings + learned outcomes.
    await _create_index(db.event_memory, 'id', unique=True)
    await _create_index(db.event_memory, 'outcome.status')
    await _create_index(db.event_memory, 'affected_symbols')

    # Proprietary dataset (L5): inference/decision logs (anonymized). Indexed by
    # recency (retention pruning) and pseudonym (right-to-erasure purge).
    await _create_index(db.inference_log, [('ts', -1)])
    await _create_index(db.inference_log, 'kind')
    await _create_index(db.inference_log, 'anon')
    await _create_index(db.decision_log, [('ts', -1)])
    await _create_index(db.decision_log, 'anon')

    # Security master (browsable multi-exchange catalog): unique per (symbol,
    # source); filters on exchange/asset_class/default_visible; name_lower for
    # case-insensitive prefix/contains search.
    await _create_index(db.security_master, [('symbol', 1), ('source', 1)], unique=True)
    await _create_index(db.security_master, 'exchange')
    await _create_index(db.security_master, 'asset_class')
    await _create_index(db.security_master, 'default_visible')
    await _create_index(db.security_master, 'source')
    await _create_index(db.security_master, 'name_lower')
