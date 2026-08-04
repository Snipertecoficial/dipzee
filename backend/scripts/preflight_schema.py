"""Apply pending migrations and validate indexes before container cutover."""
import asyncio

from database import client, db, ensure_indexes
from migrations.runner import run_pending_migrations


async def main() -> None:
    try:
        await run_pending_migrations(db)
        await ensure_indexes()
        print("Database migrations and indexes validated.")
    finally:
        client.close()


if __name__ == "__main__":
    asyncio.run(main())
