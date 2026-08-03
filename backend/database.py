"""Shared MongoDB connection for Dipzee."""
import os
from pathlib import Path
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]


async def ensure_indexes():
    """Create correctness, tenancy, expiry and query indexes.

    Index creation is part of readiness: callers intentionally let failures
    abort startup instead of serving without uniqueness/security invariants.
    """
    await db.users.create_index('email', unique=True)
    await db.users.create_index('id', unique=True)
    await db.users.create_index('stripe_customer_id', unique=True, sparse=True)
    await db.assets.create_index('ticker', unique=True)
    await db.assets.create_index([('score', -1), ('ticker', 1)])
    await db.watchlist_items.create_index('user_id')
    await db.watchlist_items.create_index('id', unique=True)
    await db.watchlist_items.create_index([('user_id', 1), ('ticker', 1)], unique=True)
    await db.alerts.create_index('user_id')
    await db.alerts.create_index('id', unique=True)
    await db.alerts.create_index('ticker')
    await db.alerts.create_index([('ticker', 1), ('active', 1)])
    await db.alert_events.create_index('user_id')
    await db.alert_events.create_index('id', unique=True)
    await db.alert_events.create_index('dedupe_key', unique=True, sparse=True)
    await db.alert_events.create_index([('user_id', 1), ('hidden', 1), ('read', 1), ('created_at', -1)])
    await db.positions.create_index('id', unique=True)
    await db.positions.create_index([('user_id', 1), ('ticker', 1)], unique=True)
    await db.password_resets.create_index('user_id', unique=True)
    await db.password_resets.create_index('token_hash', unique=True)
    await db.password_resets.create_index('purge_at', expireAfterSeconds=0)
    await db.refresh_tokens.create_index('id', unique=True)
    await db.refresh_tokens.create_index('token_hash', unique=True)
    await db.refresh_tokens.create_index('user_id')
    await db.refresh_tokens.create_index([('user_id', 1), ('family_id', 1), ('revoked', 1)])
    await db.refresh_tokens.create_index('purge_at', expireAfterSeconds=0)
    await db.login_attempts.create_index('purge_at', expireAfterSeconds=0)
    await db.user_operation_locks.create_index('expires_at', expireAfterSeconds=0)
    # Billing: unique event_id enforces webhook idempotency even under a
    # concurrent double-delivery race; unique session_id keys every reconcile/
    # poll/webhook lookup and prevents duplicate transaction rows.
    await db.stripe_events.create_index('event_id', unique=True)
    await db.stripe_events.create_index('purge_at', expireAfterSeconds=0)
    await db.payment_transactions.create_index('id', unique=True)
    await db.payment_transactions.create_index('session_id', unique=True, sparse=True, name='session_id_sparse_unique')
    await db.payment_transactions.create_index([('user_id', 1), ('created_at', -1)])
    await db.payment_transactions.create_index([('processed', 1), ('created_at', 1)])
    await db.billing_subscriptions.create_index('stripe_subscription_id', unique=True)
    await db.billing_subscriptions.create_index('user_id')
    await db.billing_subscription_events.create_index('event_id', unique=True)
    await db.billing_operation_locks.create_index('expires_at', expireAfterSeconds=0)
    await db.billing_outbox.create_index('operation_id', unique=True)
    await db.billing_outbox.create_index([('status', 1), ('next_attempt_at', 1)])

    await db.app_settings.create_index('id', unique=True)
    await db.announcements.create_index('id', unique=True)
    await db.announcements.create_index([('active', 1), ('created_at', -1)])
    await db.partner_ads.create_index('id', unique=True)
    await db.partner_ads.create_index([('active', 1), ('placement', 1)])
    await db.ai_analyses.create_index([('ticker', 1), ('locale', 1)], unique=True)
    await db.admin_audit_log.create_index('id', unique=True)
    await db.admin_audit_log.create_index([('admin_id', 1), ('created_at', -1)])
    await db.admin_audit_log.create_index('purge_at', expireAfterSeconds=0)

    # LSE intelligence layer. Normalized, point-in-time correct: the unique
    # composite keys let re-ingestion of the same period upsert in place rather
    # than duplicate rows. Only the tracked universe is stored, never the full
    # catalog, so these stay small.
    await db.lse_candles.create_index([('symbol', 1), ('timeframe', 1), ('ts', 1)], unique=True)
    await db.lse_candles.create_index([('symbol', 1), ('timeframe', 1), ('ts', -1)])
    await db.lse_fundamentals.create_index('symbol', unique=True)
    await db.lse_dividends.create_index([('symbol', 1), ('ex_date', 1)], unique=True)
    await db.lse_splits.create_index([('symbol', 1), ('date', 1)], unique=True)
    await db.lse_options_flow.create_index([('symbol', 1), ('ts', -1)])
    await db.lse_macro_series.create_index([('series', 1), ('date', 1)], unique=True)
    await db.lse_econ_calendar.create_index([('region', 1), ('date', 1)])
    await db.lse_insider.create_index([('symbol', 1), ('date', -1)])
    await db.lse_ingest_log.create_index([('at', -1)])

    # Knowledge graph (L1): nodes keyed by id, edges by src for fast fan-out.
    await db.kg_nodes.create_index('id', unique=True)
    await db.kg_nodes.create_index('kind')
    await db.kg_edges.create_index('src')
    await db.kg_edges.create_index([('src', 1), ('dst', 1)])

    # Market events (L2): unique content id (dedup), lookup by affected asset,
    # recency ordering.
    await db.market_events.create_index('id', unique=True)
    await db.market_events.create_index('affected.symbol')
    await db.market_events.create_index([('enriched_at', -1)])

    # Intelligence insight caches (L3), keyed like ai_analyses.
    await db.intel_insights.create_index([('ticker', 1), ('locale', 1)], unique=True)
    await db.intel_macro.create_index([('id', 1), ('locale', 1)], unique=True)

    # Market memory (L4): event embeddings + learned outcomes.
    await db.event_memory.create_index('id', unique=True)
    await db.event_memory.create_index('outcome.status')
    await db.event_memory.create_index('affected_symbols')

    # Proprietary dataset (L5): inference/decision logs (anonymized). Indexed by
    # recency (retention pruning) and pseudonym (right-to-erasure purge).
    await db.inference_log.create_index([('ts', -1)])
    await db.inference_log.create_index('kind')
    await db.inference_log.create_index('anon')
    await db.decision_log.create_index([('ts', -1)])
    await db.decision_log.create_index('anon')

    # Security master (browsable multi-exchange catalog): unique per (symbol,
    # source); filters on exchange/asset_class/default_visible; name_lower for
    # case-insensitive prefix/contains search.
    await db.security_master.create_index([('symbol', 1), ('source', 1)], unique=True)
    await db.security_master.create_index('exchange')
    await db.security_master.create_index('asset_class')
    await db.security_master.create_index('default_visible')
    await db.security_master.create_index('source')
    await db.security_master.create_index('name_lower')
