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


async def main(path: str) -> None:
    payload = _read_payload(path)
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
        print("Usage: python scripts/restore_backup.py <path-to-backup.json.gz.enc>")
        raise SystemExit(2)
    asyncio.run(main(sys.argv[1]))
