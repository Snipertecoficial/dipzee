"""Restore a Dipzee backup produced by backup_service.create_backup().

Reads a gzipped Extended-JSON snapshot and upserts every document by its _id
into the current database (MONGO_URL / DB_NAME from the environment — so run it
inside the backend container, which already has the scoped credentials).

Usage:
    docker compose -f docker-compose.yml -f docker-compose.prod.yml \
      exec backend python scripts/restore_backup.py /data/backups/dipzee-backup-XXATZ.json.gz

Upsert-by-_id means restoring is idempotent and non-destructive: it re-creates
missing documents and refreshes existing ones, without dropping anything the
snapshot doesn't contain. To do a clean restore, drop the collections first.
"""
import asyncio
import gzip
import os
import sys

from bson import json_util
from motor.motor_asyncio import AsyncIOMotorClient


async def main(path: str) -> None:
    with gzip.open(path, "rb") as fh:
        payload = json_util.loads(fh.read().decode("utf-8"))
    data = payload.get("data", payload)  # tolerate a raw {collection: docs} too

    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = client[os.environ["DB_NAME"]]

    total = 0
    for name, docs in data.items():
        if name == "_meta" or not isinstance(docs, list):
            continue
        for doc in docs:
            _id = doc.get("_id")
            if _id is None:
                await db[name].insert_one(doc)
            else:
                await db[name].replace_one({"_id": _id}, doc, upsert=True)
            total += 1
        print(f"  {name}: {len(docs)} docs")
    print(f"Restored {total} documents into {os.environ['DB_NAME']}.")
    client.close()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python scripts/restore_backup.py <path-to-backup.json.gz>")
        raise SystemExit(2)
    asyncio.run(main(sys.argv[1]))
