"""Restore a Dipzee backup produced by backup_service.create_backup().

Reads an authenticated encrypted Extended-JSON snapshot into the database
selected by MONGO_URL / DB_NAME. The safe default accepts only an empty target
database, preventing stale documents and migration markers from surviving a
disaster restore.

Usage:
    docker compose -f docker-compose.yml -f docker-compose.prod.yml \
      exec backend python scripts/restore_backup.py /data/backups/dipzee-backup-XXATZ.json.gz.enc

``--merge-existing`` is an explicit break-glass mode. It upserts by ``_id`` and
does not delete documents absent from the snapshot, so it is not a database or
migration rollback.
"""
import argparse
import asyncio
import base64
import gzip
import os
import sys
import tempfile

from bson import json_util
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from motor.motor_asyncio import AsyncIOMotorClient

_MAGIC = b"DIPZEEBK1"


def _backup_key() -> bytes:
    try:
        key = base64.b64decode(os.environ.get("BACKUP_ENCRYPTION_KEY", ""), validate=True)
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError("BACKUP_ENCRYPTION_KEY must be valid base64") from exc
    if len(key) != 32:
        raise RuntimeError("BACKUP_ENCRYPTION_KEY must decode to exactly 32 bytes")
    return key


def _read_payload(path: str):
    with open(path, "rb") as source:
        if source.read(len(_MAGIC)) != _MAGIC:
            raise RuntimeError("Refusing unencrypted or unsupported backup format")
        nonce = source.read(12)
        source.seek(-16, os.SEEK_END)
        tag = source.read(16)
        ciphertext_end = source.tell() - 16
        source.seek(len(_MAGIC) + 12)
        decryptor = Cipher(algorithms.AES(_backup_key()), modes.GCM(nonce, tag)).decryptor()
        with tempfile.SpooledTemporaryFile(max_size=8 * 1024 * 1024) as decrypted:
            remaining = ciphertext_end - source.tell()
            while remaining:
                chunk = source.read(min(1024 * 1024, remaining))
                if not chunk:
                    raise RuntimeError("Truncated encrypted backup")
                decrypted.write(decryptor.update(chunk))
                remaining -= len(chunk)
            decrypted.write(decryptor.finalize())
            decrypted.seek(0)
            with gzip.GzipFile(fileobj=decrypted, mode="rb") as zipped:
                return json_util.loads(zipped.read().decode("utf-8"))


def _collections(data) -> list[tuple[str, list]]:
    return [
        (name, docs)
        for name, docs in data.items()
        if name != "_meta" and isinstance(docs, list)
    ]


async def _assert_empty_target(db, collection_names: list[str]) -> None:
    occupied = []
    for name in collection_names:
        if await db[name].find_one({}, {"_id": 1}) is not None:
            occupied.append(name)
    if occupied:
        raise RuntimeError(
            "Target database is not empty; refusing a potentially inconsistent "
            "restore. Use an empty/isolated database, or pass --merge-existing "
            "only for an explicitly reviewed break-glass merge. Occupied backup "
            "collections: " + ", ".join(sorted(occupied))
        )


async def main(path: str, *, merge_existing: bool = False) -> None:
    payload = _read_payload(path)
    data = payload.get("data", payload)  # tolerate a raw {collection: docs} too
    collections = _collections(data)
    if not collections:
        raise RuntimeError("Backup contains no restorable collections")

    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = client[os.environ["DB_NAME"]]
    try:
        if not merge_existing:
            await _assert_empty_target(db, [name for name, _ in collections])

        total = 0
        for name, docs in collections:
            for doc in docs:
                _id = doc.get("_id")
                if _id is None:
                    await db[name].insert_one(doc)
                else:
                    await db[name].replace_one({"_id": _id}, doc, upsert=True)
                total += 1
            print(f"  {name}: {len(docs)} docs")
        print(f"Restored {total} documents into {os.environ['DB_NAME']}.")
    finally:
        client.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Restore an encrypted Dipzee snapshot into an empty database",
    )
    parser.add_argument("backup", help="path to dipzee-backup-*.json.gz.enc")
    parser.add_argument(
        "--merge-existing",
        action="store_true",
        help="break-glass upsert; keeps documents absent from the snapshot",
    )
    args = parser.parse_args()
    if args.merge_existing:
        print(
            "WARNING: --merge-existing is not a migration rollback and keeps "
            "out-of-snapshot documents.",
            file=sys.stderr,
        )
    asyncio.run(main(args.backup, merge_existing=args.merge_existing))
