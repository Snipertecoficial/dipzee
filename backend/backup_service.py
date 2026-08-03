"""Automated MongoDB backup — local, plus optional offsite (S3-compatible).

Why a Python-native dump instead of `mongodump`: the backend image is
python:3.11-slim and doesn't ship the mongo database tools, so we dump via
pymongo's Extended JSON (``bson.json_util``), which faithfully round-trips
ObjectIds/dates and restores exactly (see scripts/restore_backup.py).

Behavior:
- Always writes a gzipped snapshot to BACKUP_DIR (a persistent Docker volume),
  keeping the last BACKUP_KEEP files. This survives container/image redeploys
  (`git reset --hard` + `up -d` never touches named volumes), so it protects
  against the common failure — a bad migration or an accidental delete.
- If BACKUP_S3_BUCKET + keys are set, ALSO uploads the snapshot to any
  S3-compatible store (AWS S3, Backblaze B2, Cloudflare R2 …) for true offsite
  durability. No-op (local only) when unset — costs nothing until configured.

Regenerable caches are skipped to keep snapshots small; only irreplaceable data
is backed up.
"""
import base64
import gzip
import hashlib
import io
import json
import logging
import os
import secrets
from datetime import datetime, timezone

from bson import json_util
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from database import db

logger = logging.getLogger(__name__)

BACKUP_DIR = os.environ.get("BACKUP_DIR", "/data/backups")
BACKUP_KEEP = int(os.environ.get("BACKUP_KEEP", "7"))

# Regenerable from providers / recomputed on demand — no need to back these up.
SKIP_COLLECTIONS = {"market_cache", "ai_analyses"}
_MAGIC = b"DIPZEEBK1"


def _backup_key() -> bytes:
    encoded = os.environ.get("BACKUP_ENCRYPTION_KEY", "")
    try:
        key = base64.b64decode(encoded, validate=True)
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError("BACKUP_ENCRYPTION_KEY must be valid base64") from exc
    if len(key) != 32:
        raise RuntimeError("BACKUP_ENCRYPTION_KEY must decode to exactly 32 bytes")
    return key


class _EncryptWriter(io.RawIOBase):
    def __init__(self, raw, encryptor):
        self.raw = raw
        self.encryptor = encryptor

    def writable(self):
        return True

    def write(self, data):
        encrypted = self.encryptor.update(data)
        self.raw.write(encrypted)
        return len(data)

    def flush(self):
        self.raw.flush()


def _s3_client():
    """Return a boto3 S3 client if backups are configured for offsite upload,
    else None. Endpoint is optional (only needed for non-AWS S3-compatibles)."""
    bucket = os.environ.get("BACKUP_S3_BUCKET")
    access = os.environ.get("BACKUP_S3_ACCESS_KEY")
    secret = os.environ.get("BACKUP_S3_SECRET_KEY")
    if not (bucket and access and secret):
        return None
    import boto3
    kwargs = {
        "aws_access_key_id": access,
        "aws_secret_access_key": secret,
        "region_name": os.environ.get("BACKUP_S3_REGION", "us-east-1"),
    }
    endpoint = os.environ.get("BACKUP_S3_ENDPOINT")
    if endpoint:
        kwargs["endpoint_url"] = endpoint
    return boto3.client("s3", **kwargs)


def _rotate_local():
    """Keep only the newest BACKUP_KEEP snapshots on disk."""
    try:
        files = sorted(
            (f for f in os.listdir(BACKUP_DIR) if f.startswith("dipzee-backup-") and f.endswith(".json.gz.enc")),
            reverse=True,
        )
        for stale in files[BACKUP_KEEP:]:
            os.remove(os.path.join(BACKUP_DIR, stale))
    except Exception as e:  # noqa: BLE001
        logger.warning("[backup] local rotation failed: %s", e)


async def create_backup() -> dict:
    """Stream an authenticated, encrypted Extended-JSON snapshot to disk."""
    os.makedirs(BACKUP_DIR, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    fname = f"dipzee-backup-{ts}.json.gz.enc"
    fpath = os.path.join(BACKUP_DIR, fname)
    temp_path = f"{fpath}.tmp-{secrets.token_hex(8)}"
    key = _backup_key()
    nonce = secrets.token_bytes(12)
    names = [name for name in await db.list_collection_names() if name not in SKIP_COLLECTIONS]
    total_docs = 0
    try:
        with open(temp_path, "xb") as raw:
            raw.write(_MAGIC)
            raw.write(nonce)
            encryptor = Cipher(algorithms.AES(key), modes.GCM(nonce)).encryptor()
            encrypted_writer = _EncryptWriter(raw, encryptor)
            with gzip.GzipFile(fileobj=encrypted_writer, mode="wb") as zipped:
                meta = json.dumps({"created_at": ts, "collections": names}, separators=(",", ":"))
                zipped.write(f'{{"_meta":{meta},"data":{{'.encode("utf-8"))
                for collection_index, name in enumerate(names):
                    if collection_index:
                        zipped.write(b",")
                    zipped.write(json.dumps(name).encode("utf-8") + b":[")
                    first = True
                    async for doc in db[name].find({}):
                        if not first:
                            zipped.write(b",")
                        zipped.write(json_util.dumps(doc, separators=(",", ":")).encode("utf-8"))
                        first = False
                        total_docs += 1
                    zipped.write(b"]")
                zipped.write(b"}}")
            encrypted_writer.close()
            raw.write(encryptor.finalize())
            raw.write(encryptor.tag)
            raw.flush()
            os.fsync(raw.fileno())
        try:
            os.chmod(temp_path, 0o600)
        except OSError:
            pass
        os.replace(temp_path, fpath)
    except Exception:
        try:
            os.remove(temp_path)
        except FileNotFoundError:
            pass
        raise
    _rotate_local()

    size = os.path.getsize(fpath)
    digest = hashlib.sha256()
    with open(fpath, "rb") as backup_file:
        for chunk in iter(lambda: backup_file.read(1024 * 1024), b""):
            digest.update(chunk)
    result = {"file": fname, "collections": len(names), "documents": total_docs,
              "bytes": size, "sha256": digest.hexdigest(), "offsite": False}

    client = _s3_client()
    if client:
        bucket = os.environ.get("BACKUP_S3_BUCKET")
        prefix = os.environ.get("BACKUP_S3_PREFIX", "dipzee-backups").strip("/")
        key = f"{prefix}/{fname}" if prefix else fname
        try:
            extra_args = {
                "ContentType": "application/octet-stream",
                "Metadata": {"sha256": result["sha256"]},
            }
            if os.environ.get("BACKUP_S3_SSE", "AES256"):
                extra_args["ServerSideEncryption"] = os.environ.get("BACKUP_S3_SSE", "AES256")
            client.upload_file(fpath, bucket, key, ExtraArgs=extra_args)
            result["offsite"] = True
            result["offsite_key"] = key
        except Exception as e:  # noqa: BLE001
            logger.error("[backup] offsite upload failed (local snapshot kept): %s", e)

    logger.info("[backup] snapshot %s: %d collections, %d docs, %d bytes, offsite=%s",
                fname, result["collections"], result["documents"], result["bytes"], result["offsite"])
    return result


def list_local_backups() -> list:
    """Recent local snapshots, newest first (for the admin panel)."""
    try:
        files = []
        for f in os.listdir(BACKUP_DIR):
            if f.startswith("dipzee-backup-") and f.endswith(".json.gz.enc"):
                p = os.path.join(BACKUP_DIR, f)
                files.append({"file": f, "bytes": os.path.getsize(p), "modified": os.path.getmtime(p)})
        return sorted(files, key=lambda x: x["modified"], reverse=True)
    except FileNotFoundError:
        return []
