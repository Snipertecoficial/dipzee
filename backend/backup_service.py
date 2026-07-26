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
import gzip
import logging
import os
from datetime import datetime, timezone

from bson import json_util

from database import db

logger = logging.getLogger(__name__)

BACKUP_DIR = os.environ.get("BACKUP_DIR", "/data/backups")
BACKUP_KEEP = int(os.environ.get("BACKUP_KEEP", "7"))

# Regenerable from providers / recomputed on demand — no need to back these up.
SKIP_COLLECTIONS = {"market_cache", "ai_analyses"}


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
            (f for f in os.listdir(BACKUP_DIR) if f.startswith("dipzee-backup-") and f.endswith(".json.gz")),
            reverse=True,
        )
        for stale in files[BACKUP_KEEP:]:
            os.remove(os.path.join(BACKUP_DIR, stale))
    except Exception as e:  # noqa: BLE001
        logger.warning("[backup] local rotation failed: %s", e)


async def create_backup() -> dict:
    """Dump all non-cache collections to a gzipped Extended-JSON snapshot
    (local always; offsite if configured). Returns a summary dict."""
    os.makedirs(BACKUP_DIR, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    fname = f"dipzee-backup-{ts}.json.gz"
    fpath = os.path.join(BACKUP_DIR, fname)

    data = {}
    total_docs = 0
    for name in await db.list_collection_names():
        if name in SKIP_COLLECTIONS:
            continue
        docs = await db[name].find({}).to_list(length=None)
        data[name] = docs
        total_docs += len(docs)

    payload = json_util.dumps({"_meta": {"created_at": ts, "collections": list(data)}, "data": data})
    blob = gzip.compress(payload.encode("utf-8"))
    with open(fpath, "wb") as fh:
        fh.write(blob)
    _rotate_local()

    result = {"file": fname, "collections": len(data), "documents": total_docs,
              "bytes": len(blob), "offsite": False}

    client = _s3_client()
    if client:
        bucket = os.environ.get("BACKUP_S3_BUCKET")
        prefix = os.environ.get("BACKUP_S3_PREFIX", "dipzee-backups").strip("/")
        key = f"{prefix}/{fname}" if prefix else fname
        try:
            client.put_object(Bucket=bucket, Key=key, Body=blob)
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
            if f.startswith("dipzee-backup-") and f.endswith(".json.gz"):
                p = os.path.join(BACKUP_DIR, f)
                files.append({"file": f, "bytes": os.path.getsize(p), "modified": os.path.getmtime(p)})
        return sorted(files, key=lambda x: x["modified"], reverse=True)
    except FileNotFoundError:
        return []
