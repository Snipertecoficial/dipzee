#!/usr/bin/env python3
"""Verify that a Dipzee deploy actually reached production.

The CI pipeline builds the backend image with the git commit baked in
(GIT_SHA build-arg -> /api/health `commit`). This script polls the live
health endpoint and compares the deployed commit to the one you expect
(local HEAD by default), so "did my push actually go live?" is a single
command instead of guessing.

Usage:
    python scripts/verify_deploy.py                 # expect local HEAD @ dipzee.com
    python scripts/verify_deploy.py --sha <sha>     # expect a specific commit
    python scripts/verify_deploy.py --url https://staging.example.com
    python scripts/verify_deploy.py --timeout 1200  # wait up to 20 min

Exit code 0 when the live commit matches (and health is "ok"); 1 otherwise.
Stdlib only — no dependencies, runs anywhere.
"""
import argparse
import json
import subprocess
import sys
import time
import urllib.request

DEFAULT_URL = "https://dipzee.com"

# The success/failure lines use emoji; on a legacy Windows console (cp1252) a raw
# print would raise UnicodeEncodeError — which, mid-poll, gets swallowed as "not
# reachable yet" and the script keeps looping past an already-successful deploy.
# Force UTF-8 on the streams so the result is always printed (and reported) correctly.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except (AttributeError, ValueError):  # pragma: no cover - older/odd streams
        pass


def local_head() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:  # noqa: BLE001
        return ""


def fetch_health(base_url: str, timeout: float = 8.0) -> dict:
    url = base_url.rstrip("/") + "/api/health"
    with urllib.request.urlopen(url, timeout=timeout) as resp:  # noqa: S310 (trusted URL)
        return json.loads(resp.read().decode("utf-8"))


def main() -> int:
    p = argparse.ArgumentParser(description="Verify a Dipzee deploy is live.")
    p.add_argument("--url", default=DEFAULT_URL, help="site base URL (default: %(default)s)")
    p.add_argument("--sha", default=None, help="commit to expect (default: local git HEAD)")
    p.add_argument("--timeout", type=int, default=1200, help="max seconds to wait (default: 1200)")
    p.add_argument("--interval", type=int, default=15, help="seconds between polls (default: 15)")
    args = p.parse_args()

    expected = (args.sha or local_head()).strip()
    if not expected:
        print("could not determine expected commit (pass --sha or run inside the git repo)", file=sys.stderr)
        return 1
    short = expected[:12]
    print(f"expecting commit {short} live at {args.url} (waiting up to {args.timeout}s)\n")

    deadline = time.time() + args.timeout
    last = None
    while time.time() < deadline:
        try:
            h = fetch_health(args.url)
            live = (h.get("commit") or "").strip()
            status = h.get("status")
            if live != last:
                print(f"[{time.strftime('%H:%M:%S')}] live commit={live[:12] or '?'} status={status}")
                last = live
            if live == expected and status == "ok":
                print(f"\n✅ DEPLOYED — {short} is live and healthy.")
                return 0
            if live == expected and status != "ok":
                print(f"\n⚠️  {short} is live but health={status} (check the containers).")
                return 1
        except Exception as e:  # noqa: BLE001
            print(f"[{time.strftime('%H:%M:%S')}] not reachable yet: {e}")
        time.sleep(args.interval)

    print(f"\n❌ TIMEOUT — {short} did not go live within {args.timeout}s. "
          f"Check the GitHub Actions 'Deploy to VPS' run (build/test/push or SSH step may have failed).",
          file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
