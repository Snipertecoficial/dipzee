#!/usr/bin/env python3
"""Bootstrap the small set of security settings introduced after launch.

This script is intentionally stdlib-only because it runs on the VPS host before
the new application image starts. Existing non-empty secrets are never rotated.
Generated values are not printed; only setting names are reported.
"""
from __future__ import annotations

import argparse
import base64
import os
from pathlib import Path
import re
import secrets
import stat
import tempfile
from urllib.parse import urlparse


_ASSIGNMENT = re.compile(
    r"^(?P<prefix>\s*(?:export\s+)?)"
    r"(?P<key>[A-Za-z_][A-Za-z0-9_]*)\s*=\s*(?P<value>.*?)(?P<newline>\r?\n)?$"
)
_BOOTSTRAPPED = {
    "ENV",
    "PUBLIC_APP_URL",
    "APP_ENCRYPTION_KEY",
    "ADMIN_MFA_REQUIRED",
    "DATASET_SALT",
    "BACKUP_ENCRYPTION_KEY",
}
_REQUIRED = (
    "ENV",
    "DOMAIN",
    "MONGO_ROOT_USER",
    "MONGO_ROOT_PASSWORD",
    "MONGO_APP_USER",
    "MONGO_APP_PASSWORD",
    "DB_NAME",
    "JWT_SECRET",
    "PUBLIC_APP_URL",
    "CORS_ORIGINS",
    "APP_ENCRYPTION_KEY",
    "ADMIN_MFA_REQUIRED",
    "DATASET_SALT",
    "RESEND_API_KEY",
    "STRIPE_API_KEY",
    "STRIPE_PUBLISHABLE_KEY",
    "STRIPE_WEBHOOK_SECRET",
    "SUPERADMIN_EMAIL",
    "SUPERADMIN_PASSWORD",
    "BACKUP_ENCRYPTION_KEY",
)


def _plain_value(raw: str) -> str:
    value = raw.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def _index(lines: list[str]) -> dict[str, tuple[int, str]]:
    entries: dict[str, tuple[int, str]] = {}
    duplicates: set[str] = set()
    for number, line in enumerate(lines):
        match = _ASSIGNMENT.match(line)
        if not match:
            continue
        key = match.group("key")
        if key in entries:
            duplicates.add(key)
        else:
            entries[key] = (number, _plain_value(match.group("value")))
    relevant = sorted(duplicates.intersection(set(_REQUIRED)))
    if relevant:
        raise RuntimeError(
            "Duplicate production settings must be resolved: " + ", ".join(relevant)
        )
    return entries


def _set(lines: list[str], key: str, value: str) -> None:
    entries = _index(lines)
    if key in entries:
        number, _ = entries[key]
        newline = "\r\n" if lines[number].endswith("\r\n") else "\n"
        lines[number] = f"{key}={value}{newline}"
        return
    if lines and not lines[-1].endswith(("\n", "\r")):
        lines[-1] += "\n"
    lines.append(f"{key}={value}\n")


def _decode_key(name: str, value: str) -> bytes:
    try:
        decoded = base64.b64decode(value, validate=True)
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"{name} must be valid base64") from exc
    if len(decoded) != 32:
        raise RuntimeError(f"{name} must decode to exactly 32 bytes")
    return decoded


def _validate_public_url(value: str) -> None:
    parsed = urlparse(value)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.path not in {"", "/"}
        or parsed.params
        or parsed.query
        or parsed.fragment
    ):
        raise RuntimeError("PUBLIC_APP_URL must be an explicit HTTPS origin")


def _atomic_write(path: Path, content: str) -> None:
    descriptor, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temp_path = Path(temp_name)
    try:
        os.chmod(temp_path, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
        os.chmod(path, 0o600)
        try:
            directory_fd = os.open(path.parent, os.O_RDONLY)
        except OSError:
            return
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        try:
            temp_path.unlink()
        except FileNotFoundError:
            pass


def bootstrap(path: Path, public_url: str) -> dict[str, list[str]]:
    if path.is_symlink():
        raise RuntimeError("Refusing to replace a symlinked production environment file")
    info = path.stat()
    if not stat.S_ISREG(info.st_mode):
        raise RuntimeError("Production environment path is not a regular file")
    if info.st_size > 1024 * 1024:
        raise RuntimeError("Production environment file is unexpectedly large")
    _validate_public_url(public_url)

    original = path.read_text(encoding="utf-8")
    lines = original.splitlines(keepends=True)
    generated: list[str] = []
    updated: list[str] = []

    entries = _index(lines)
    # Admin MFA is deliberately opt-in: forcing it on locked out the existing
    # superadmin (no enrolment) with a 403 on every /admin/* route. Bootstrap
    # keeps the key managed (so it converges to a known value across deploys)
    # but defaults it OFF; flip to "true" here once an authenticator is enrolled.
    desired_fixed = {
        "ENV": "production",
        "ADMIN_MFA_REQUIRED": "false",
    }
    for key, desired in desired_fixed.items():
        if entries.get(key, (None, ""))[1].lower() != desired:
            _set(lines, key, desired)
            updated.append(key)
            entries = _index(lines)

    if not entries.get("PUBLIC_APP_URL", (None, ""))[1]:
        _set(lines, "PUBLIC_APP_URL", public_url)
        updated.append("PUBLIC_APP_URL")
        entries = _index(lines)

    for key in ("APP_ENCRYPTION_KEY", "BACKUP_ENCRYPTION_KEY"):
        if not entries.get(key, (None, ""))[1]:
            _set(lines, key, base64.b64encode(secrets.token_bytes(32)).decode("ascii"))
            generated.append(key)
            entries = _index(lines)

    if not entries.get("DATASET_SALT", (None, ""))[1]:
        _set(lines, "DATASET_SALT", secrets.token_hex(32))
        generated.append("DATASET_SALT")
        entries = _index(lines)

    values = {key: entries.get(key, (None, ""))[1] for key in _REQUIRED}
    missing = [key for key, value in values.items() if not value]
    if missing:
        raise RuntimeError("Missing required production settings: " + ", ".join(missing))

    if values["ENV"] != "production":
        raise RuntimeError("ENV must be production")
    _validate_public_url(values["PUBLIC_APP_URL"])
    if values["PUBLIC_APP_URL"].rstrip("/") != public_url.rstrip("/"):
        raise RuntimeError("PUBLIC_APP_URL does not match the approved production origin")
    cors_origins = {item.strip().rstrip("/") for item in values["CORS_ORIGINS"].split(",") if item.strip()}
    if public_url.rstrip("/") not in cors_origins:
        raise RuntimeError("CORS_ORIGINS must include the approved production origin")
    # ADMIN_MFA_REQUIRED is intentionally allowed to be off (see desired_fixed);
    # it is validated only as a well-formed boolean so a typo can't silently
    # leave the gate in an undefined state.
    if values["ADMIN_MFA_REQUIRED"].lower() not in {"1", "true", "yes", "0", "false", "no"}:
        raise RuntimeError("ADMIN_MFA_REQUIRED must be a boolean value")
    if len(values["JWT_SECRET"]) < 32 or len(values["DATASET_SALT"]) < 32:
        raise RuntimeError("JWT_SECRET and DATASET_SALT must contain at least 32 characters")
    app_key = _decode_key("APP_ENCRYPTION_KEY", values["APP_ENCRYPTION_KEY"])
    backup_key = _decode_key("BACKUP_ENCRYPTION_KEY", values["BACKUP_ENCRYPTION_KEY"])
    if app_key == backup_key:
        raise RuntimeError("Application and backup encryption keys must be independent")
    if values["DATASET_SALT"] == values["JWT_SECRET"]:
        raise RuntimeError("DATASET_SALT must be independent from JWT_SECRET")

    content = "".join(lines)
    if content != original:
        _atomic_write(path, content)
    else:
        os.chmod(path, 0o600)
    return {"generated": generated, "updated": updated}


def main() -> int:
    parser = argparse.ArgumentParser(description="Bootstrap Dipzee production settings safely")
    parser.add_argument("--env-file", type=Path, default=Path(".env"))
    parser.add_argument("--public-url", default="https://dipzee.com")
    args = parser.parse_args()
    result = bootstrap(args.env_file, args.public_url)
    changed = result["generated"] + result["updated"]
    if changed:
        print("Production environment prepared; changed setting names: " + ", ".join(changed))
    else:
        print("Production environment already satisfies the deploy preflight.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
