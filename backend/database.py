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
