"""Discovers and applies pending data migrations on backend startup.

A migration is a file in this package named ``NNNN_description.py`` (e.g.
``0001_backfill_user_locale.py``) exposing an ``async def up(db): ...``. Each
one runs at most once, tracked by filename in ``db.schema_migrations``, in
filename order. There is deliberately no ``down()``/rollback — for a team
this size, "write a new forward migration to correct a mistake" is simpler
to reason about than a rollback path that's rarely exercised and easy to get
wrong. Numbers are never reused or renumbered once a migration has shipped.

Unlike ``ensure_indexes()``/``seed_superadmin()`` (safe to log-and-continue
on failure — a missing index or unseeded admin degrades gracefully), a
migration failure here is re-raised and aborts startup: for an app handling
real payments, staying down beats coming up with half-applied data. See
server.py's startup handler for how this is wired in.
"""
import importlib
import logging
import pkgutil
import re
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

_MIGRATION_NAME_RE = re.compile(r"^\d{4}_[a-z0-9_]+$")


def _discover() -> list:
    """Migration module names in this package, in filename order."""
    pkg_dir = Path(__file__).parent
    names = [
        name for _, name, is_pkg in pkgutil.iter_modules([str(pkg_dir)])
        if not is_pkg and _MIGRATION_NAME_RE.match(name)
    ]
    return sorted(names)


async def run_pending_migrations(db) -> None:
    all_migrations = _discover()
    if not all_migrations:
        logger.info("[migrations] none defined.")
        return

    applied_docs = await db.schema_migrations.find({}, {"_id": 1}).to_list(None)
    applied = {d["_id"] for d in applied_docs}
    pending = [name for name in all_migrations if name not in applied]

    if not pending:
        logger.info("[migrations] up to date (%d applied).", len(applied))
        return

    for name in pending:
        logger.info("[migrations] applying %s ...", name)
        module = importlib.import_module(f"migrations.{name}")
        await module.up(db)
        await db.schema_migrations.insert_one({
            "_id": name,
            "applied_at": datetime.now(timezone.utc).isoformat(),
        })
        logger.info("[migrations] applied %s.", name)
