#!/usr/bin/env python3
"""Pull a fresh production database snapshot and restore it into the local
Docker MongoDB — so you can test on localhost with real data.

Usage (from the repo root):
    python pull_production_db.py

It will:
 1. Log in to the production API as superadmin.
 2. Trigger a fresh backup and download it.
 3. Restore every collection into the local Mongo container.

Requirements: Python 3.10+, `requests` (pip install requests).
The local stack must already be running:
    docker compose -f docker-compose.yml -f docker-compose.local.yml up -d --build mongo backend frontend
"""

import gzip
import json
import os
import subprocess
import sys
import tempfile

try:
    import requests
except ImportError:
    print("ERROR: 'requests' is required. Install with: pip install requests")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Configuration — reads from .env automatically so you don't have to type
# credentials every time.
# ---------------------------------------------------------------------------

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = SCRIPT_DIR  # script lives at repo root

def _load_dotenv() -> dict:
    """Minimalist .env parser (no third-party dep)."""
    env = {}
    dotenv_path = os.path.join(REPO_ROOT, ".env")
    if not os.path.isfile(dotenv_path):
        return env
    with open(dotenv_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env

dotenv = _load_dotenv()

# Production URL — the live site
PROD_URL = os.environ.get("DIPZEE_PROD_URL") or dotenv.get("DIPZEE_PROD_URL") or "https://dipzee.com"

# Superadmin credentials for the PRODUCTION site.
# These can be set as env vars or will be prompted interactively.
PROD_EMAIL = os.environ.get("DIPZEE_PROD_EMAIL") or dotenv.get("SUPERADMIN_EMAIL") or ""
PROD_PASSWORD = os.environ.get("DIPZEE_PROD_PASSWORD") or ""

BACKUP_DIR = os.path.join(REPO_ROOT, "backups")

# ---------------------------------------------------------------------------

def login(session: requests.Session, base_url: str, email: str, password: str) -> str:
    """Log in and return the access token."""
    r = session.post(f"{base_url}/api/login", json={"email": email, "password": password}, timeout=30)
    if r.status_code == 401:
        print("ERROR: Invalid email or password on the production site.")
        sys.exit(1)
    r.raise_for_status()
    token = r.json().get("access_token")
    if not token:
        print(f"ERROR: unexpected login response: {r.text[:300]}")
        sys.exit(1)
    return token


def download_backup(session: requests.Session, base_url: str, token: str, dest: str) -> str:
    """Trigger + download the latest backup. Returns the local file path."""
    headers = {"Authorization": f"Bearer {token}"}

    print("  → Triggering a fresh backup on production...")
    r = session.post(f"{base_url}/api/admin/backup/run", headers=headers, timeout=120)
    r.raise_for_status()
    info = r.json()
    print(f"    Backup created: {info.get('file')} ({info.get('documents', '?')} docs, {info.get('bytes', '?')} bytes)")

    print("  → Downloading backup...")
    r = session.get(f"{base_url}/api/admin/backup/download", headers=headers, timeout=120, stream=True)
    r.raise_for_status()
    cd = r.headers.get("content-disposition", "")
    fname = "production-backup.json.gz"
    if "filename=" in cd:
        fname = cd.split("filename=")[-1].strip('"').strip()
    fpath = os.path.join(dest, fname)
    with open(fpath, "wb") as f:
        for chunk in r.iter_content(chunk_size=65536):
            f.write(chunk)
    size_kb = os.path.getsize(fpath) / 1024
    print(f"    Saved to {fpath} ({size_kb:.0f} KB)")
    return fpath


def restore_to_local(backup_path: str) -> None:
    """Decompress the backup and import every collection into the local
    Docker Mongo via the running backend container."""
    print("  → Decompressing backup...")
    with gzip.open(backup_path, "rb") as f:
        payload = json.loads(f.read().decode("utf-8"))
    data = payload.get("data", payload)

    collections = {k: v for k, v in data.items() if k != "_meta" and isinstance(v, list) and v}
    print(f"    Found {len(collections)} collections: {', '.join(collections.keys())}")

    for col_name, docs in collections.items():
        print(f"  → Restoring {col_name} ({len(docs)} docs)...")
        # Serialize documents to JSON, encode as base64 for safe shell transit
        import base64
        b64 = base64.b64encode(json.dumps(docs, default=str, ensure_ascii=False).encode("utf-8")).decode()

        py_script = (
            f"import json,base64,os;"
            f"from pymongo import MongoClient;"
            f"from bson import json_util;"
            f"data=json_util.loads(base64.b64decode('{b64}'));"
            f"c=MongoClient(os.environ['MONGO_URL']);"
            f"db=c.get_default_database();"
            f"db['{col_name}'].drop();"
            f"r=db['{col_name}'].insert_many(data);"
            f"print(f'{col_name}: {{len(r.inserted_ids)}} docs restored');"
            f"c.close()"
        )

        result = subprocess.run(
            ["docker", "exec", "dipzee-backend-1", "python3", "-c", py_script],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            print(f"    ERROR: {result.stderr.strip()}")
        else:
            print(f"    {result.stdout.strip()}")

    print("\n✅ All collections restored to local database!")


def main():
    print("=" * 60)
    print("  Dipzee — Pull Production DB to Local")
    print("=" * 60)

    email = PROD_EMAIL
    password = PROD_PASSWORD

    if not email:
        email = input("Production superadmin email: ").strip()
    if not password:
        import getpass
        password = getpass.getpass("Production superadmin password: ")

    print(f"\n[1/3] Logging in to {PROD_URL}...")
    session = requests.Session()
    token = login(session, PROD_URL, email, password)
    print("    ✓ Authenticated as superadmin\n")

    print("[2/3] Downloading fresh production backup...")
    os.makedirs(BACKUP_DIR, exist_ok=True)
    backup_path = download_backup(session, PROD_URL, token, BACKUP_DIR)
    print()

    print("[3/3] Restoring into local Docker MongoDB...")
    restore_to_local(backup_path)

    print()
    print("=" * 60)
    print("  Done! Open http://localhost:8080 and log in with your")
    print("  real production credentials.")
    print("=" * 60)


if __name__ == "__main__":
    main()
