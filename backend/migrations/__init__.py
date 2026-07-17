"""One-off data migrations, run automatically on backend startup.

See runner.py for how these get discovered and applied. Index creation and
superadmin seeding are handled separately (database.py / server.py) and
don't belong here — this package is only for data transformations that
those two mechanisms can't express (backfills, renames, one-time cleanups).
"""
