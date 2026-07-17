"""One-off importer for a JSON export of the Dipzee MongoDB.

Expects the shape produced by the Emergent DB viewer export:
``{"collection_name": [doc, doc, ...], ...}``. Dates/ids in that export are
already plain strings, matching how the app itself stores them (see
``database.py`` / ``routes_auth.py``, which write ``created_at`` etc. as
``isoformat()`` strings) — no type conversion needed.

Upserts every document by its "_id", so re-running the script is safe and
won't duplicate data.

Usage:
    MONGO_URL=... DB_NAME=... python scripts/import_backup.py /path/to/backup.json
"""
import json
import os
import sys

from pymongo import MongoClient


def main():
    if len(sys.argv) != 2:
        print("Usage: python import_backup.py <backup.json>")
        sys.exit(1)

    backup_path = sys.argv[1]
    mongo_url = os.environ["MONGO_URL"]
    db_name = os.environ["DB_NAME"]

    with open(backup_path, "r", encoding="utf-8") as f:
        backup = json.load(f)

    client = MongoClient(mongo_url)
    db = client[db_name]

    print(f"Importing into database '{db_name}'")
    total = 0
    for collection_name, docs in backup.items():
        if not isinstance(docs, list):
            continue
        coll = db[collection_name]
        for doc in docs:
            doc_id = doc.get("_id")
            if doc_id is None:
                coll.insert_one(doc)
            else:
                coll.replace_one({"_id": doc_id}, doc, upsert=True)
        total += len(docs)
        print(f"  {collection_name}: {len(docs)} documents")

    print(f"Done. {total} documents across {len(backup)} collections.")
    client.close()


if __name__ == "__main__":
    main()
