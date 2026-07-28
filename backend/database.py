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
    """Create indexes on user_id and ticker as required."""
    await db.users.create_index('email', unique=True)
    await db.assets.create_index('ticker', unique=True)
    await db.watchlist_items.create_index('user_id')
    await db.watchlist_items.create_index([('user_id', 1), ('ticker', 1)], unique=True)
    await db.alerts.create_index('user_id')
    await db.alerts.create_index('ticker')
    await db.alert_events.create_index('user_id')
    await db.alert_events.create_index([('user_id', 1), ('read', 1)])
    await db.positions.create_index([('user_id', 1), ('ticker', 1)], unique=True)
    await db.password_resets.create_index('user_id', unique=True)
    await db.password_resets.create_index('token_hash')
    await db.refresh_tokens.create_index('token_hash')
    await db.refresh_tokens.create_index('user_id')
    # Billing: unique event_id enforces webhook idempotency even under a
    # concurrent double-delivery race; unique session_id keys every reconcile/
    # poll/webhook lookup and prevents duplicate transaction rows.
    await db.stripe_events.create_index('event_id', unique=True)
    await db.payment_transactions.create_index('session_id', unique=True)
    await db.billing_subscriptions.create_index('stripe_subscription_id', unique=True)

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
