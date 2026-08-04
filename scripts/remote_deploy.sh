#!/usr/bin/env bash
set -Eeuo pipefail

# Runs on the VPS from the checked-out repository. It deliberately emits only
# non-secret metadata; GitHub Actions owns SSH setup and artifact retention.

compose_files=(-f docker-compose.yml -f docker-compose.prod.yml)

die() {
  printf 'deploy error: %s\n' "$*" >&2
  exit 1
}

valid_sha() {
  [[ "${1:-}" =~ ^[0-9a-f]{40}$ ]]
}

compose_for() {
  local image_tag=$1
  shift
  BACKEND_IMAGE_TAG="$image_tag" FRONTEND_IMAGE_TAG="$image_tag" IMAGE_TAG="$image_tag" \
    docker compose "${compose_files[@]}" "$@"
}

compose_tags() {
  local backend_tag=$1
  local frontend_tag=$2
  shift 2
  BACKEND_IMAGE_TAG="$backend_tag" FRONTEND_IMAGE_TAG="$frontend_tag" \
    docker compose "${compose_files[@]}" "$@"
}

prepare() {
  local image_tag=${1:-}
  local ghcr_user=${2:-}
  local run_id=${3:-}
  valid_sha "$image_tag" || die "invalid image tag"
  [[ "$ghcr_user" =~ ^[A-Za-z0-9_][A-Za-z0-9_-]{0,100}(\[bot\])?$ ]] || die "invalid registry user"
  [[ "$run_id" =~ ^[0-9]+$ ]] || die "invalid workflow run id"
  [[ -f .env && ! -L .env ]] || die ".env must be a regular non-symlink file"
  [[ "$(git rev-parse HEAD)" == "$image_tag" ]] || die "checkout does not match release SHA"
  umask 077

  python3 scripts/bootstrap_production_env.py \
    --env-file .env \
    --public-url https://dipzee.com

  trap 'docker logout ghcr.io >/dev/null 2>&1 || true' EXIT
  docker login ghcr.io -u "$ghcr_user" --password-stdin >/dev/null
  compose_for "$image_tag" pull backend frontend
  compose_for "$image_tag" run --rm --no-deps -T backend \
    python -c 'from app_config import validate_production_config; validate_production_config(); print("Application configuration validated.")'

  local backup_json
  backup_json=$(compose_for "$image_tag" run --rm --no-deps -T backend \
    python -c 'import asyncio,json; from backup_service import create_backup; print(json.dumps(asyncio.run(create_backup()), separators=(",",":")))')

  local fields
  fields=$(printf '%s' "$backup_json" | python3 -c '
import json, re, sys
result = json.load(sys.stdin)
name = result.get("file", "")
digest = result.get("sha256", "")
size = result.get("bytes", 0)
collections = result.get("collections", 0)
documents = result.get("documents", 0)
if not re.fullmatch(r"dipzee-backup-[0-9]{8}T[0-9]{12}Z[.]json[.]gz[.]enc", name):
    raise SystemExit("invalid backup filename")
if not re.fullmatch(r"[0-9a-f]{64}", digest):
    raise SystemExit("invalid backup digest")
if not isinstance(size, int) or size <= 0:
    raise SystemExit("empty backup")
if not isinstance(collections, int) or collections <= 0:
    raise SystemExit("backup contains no collections")
if not isinstance(documents, int) or documents <= 0:
    raise SystemExit("backup contains no documents")
print(name)
print(digest)
print(size)
print(collections)
print(documents)
')
  local backup_file backup_sha backup_bytes backup_collections backup_documents
  backup_file=$(printf '%s\n' "$fields" | sed -n '1p')
  backup_sha=$(printf '%s\n' "$fields" | sed -n '2p')
  backup_bytes=$(printf '%s\n' "$fields" | sed -n '3p')
  backup_collections=$(printf '%s\n' "$fields" | sed -n '4p')
  backup_documents=$(printf '%s\n' "$fields" | sed -n '5p')
  [[ "$backup_collections" =~ ^[1-9][0-9]*$ ]] || die "backup contains no collections"
  [[ "$backup_documents" =~ ^[1-9][0-9]*$ ]] || die "backup contains no documents"
  compose_for "$image_tag" run --rm --no-deps -T backend \
    python -c 'import sys; from scripts.restore_backup import _read_payload; payload=_read_payload(sys.argv[1]); users=payload.get("data", {}).get("users"); assert isinstance(users, list) and users, "backup has no users"; print("Backup authentication and critical collection check passed.")' \
    "/data/backups/$backup_file"

  local stage_dir stage_path key_path actual_sha actual_bytes
  stage_dir=$(mktemp -d "/tmp/dipzee-deploy-${run_id}.XXXXXX")
  stage_path="$stage_dir/$backup_file"
  key_path="$stage_dir/recovery-key"
  cleanup_failed_stage() {
    rm -f -- "$stage_path"
    rm -f -- "$key_path"
    rmdir -- "$stage_dir" 2>/dev/null || true
  }
  trap cleanup_failed_stage ERR INT TERM
  compose_for "$image_tag" run --rm --no-deps -T backend \
    sh -c 'case "$1" in dipzee-backup-*.json.gz.enc) cat -- "/data/backups/$1" ;; *) exit 2 ;; esac' \
    _ "$backup_file" > "$stage_path"
  chmod 600 "$stage_path"
  actual_sha=$(sha256sum "$stage_path" | awk '{print $1}')
  actual_bytes=$(wc -c < "$stage_path" | tr -d '[:space:]')
  [[ "$actual_sha" == "$backup_sha" ]] || die "staged backup digest mismatch"
  [[ "$actual_bytes" == "$backup_bytes" ]] || die "staged backup size mismatch"
  python3 -c 'import os,sys; from pathlib import Path; from scripts.bootstrap_production_env import _decode_key,_index; entries=_index(Path(sys.argv[1]).read_text(encoding="utf-8").splitlines(keepends=True)); value=entries["BACKUP_ENCRYPTION_KEY"][1]; _decode_key("BACKUP_ENCRYPTION_KEY", value); fd=os.open(sys.argv[2], os.O_WRONLY|os.O_CREAT|os.O_EXCL, 0o600); os.write(fd, value.encode("ascii")); os.close(fd)' \
    .env "$key_path"
  trap - ERR INT TERM

  printf 'BACKUP_REMOTE_PATH=%s\n' "$stage_path"
  printf 'BACKUP_KEY_REMOTE_PATH=%s\n' "$key_path"
  printf 'BACKUP_FILE=%s\n' "$backup_file"
  printf 'BACKUP_SHA256=%s\n' "$backup_sha"
  printf 'BACKUP_BYTES=%s\n' "$backup_bytes"
}

cleanup() {
  local path=${1:-}
  [[ "$path" =~ ^/tmp/dipzee-deploy-[0-9]+[.][A-Za-z0-9]+/dipzee-backup-[0-9]{8}T[0-9]{12}Z[.]json[.]gz[.]enc$ ]] \
    || die "refusing unsafe cleanup path"
  rm -f -- "$path" "${path%/*}/recovery-key"
  rmdir -- "${path%/*}"
}

activate() {
  local image_tag=${1:-}
  local ghcr_user=${2:-}
  local run_id=${3:-}
  valid_sha "$image_tag" || die "invalid image tag"
  [[ "$ghcr_user" =~ ^[A-Za-z0-9_][A-Za-z0-9_-]{0,100}(\[bot\])?$ ]] || die "invalid registry user"
  [[ "$run_id" =~ ^[0-9]+$ ]] || die "invalid workflow run id"
  [[ "$(git rev-parse HEAD)" == "$image_tag" ]] || die "checkout does not match release SHA"

  trap 'docker logout ghcr.io >/dev/null 2>&1 || true' EXIT
  docker login ghcr.io -u "$ghcr_user" --password-stdin >/dev/null

  # Apply forward-compatible schema changes before replacing the currently
  # healthy containers. A schema/index failure leaves the old release serving
  # traffic and emits the precise Python/Mongo error to the protected run log.
  compose_for "$image_tag" run --rm --no-deps -T backend \
    python -m scripts.preflight_schema

  local backend_id frontend_id backend_image_id frontend_image_id
  backend_id=$(docker compose "${compose_files[@]}" ps -q backend)
  frontend_id=$(docker compose "${compose_files[@]}" ps -q frontend)
  backend_image_id=$(docker inspect --format='{{.Image}}' "$backend_id")
  frontend_image_id=$(docker inspect --format='{{.Image}}' "$frontend_id")

  local rollback_backend_tag="rollback-${run_id}"
  local rollback_frontend_tag="rollback-${run_id}"
  docker image tag "$backend_image_id" "ghcr.io/snipertecoficial/dipzee-backend:$rollback_backend_tag"
  docker image tag "$frontend_image_id" "ghcr.io/snipertecoficial/dipzee-frontend:$rollback_frontend_tag"
  local state_file="/tmp/dipzee-rollback-${run_id}"
  umask 077
  printf '%s\n%s\n' "$rollback_backend_tag" "$rollback_frontend_tag" > "$state_file"

  rollback() {
    printf 'Release failed readiness; restoring the exact previous image IDs.\n' >&2
    compose_tags "$rollback_backend_tag" "$rollback_frontend_tag" \
      up -d --pull never --wait --wait-timeout 180
  }

  report_backend_health() {
    local failed_backend_id
    failed_backend_id=$(docker compose "${compose_files[@]}" ps -q backend 2>/dev/null || true)
    [[ -n "$failed_backend_id" ]] || return 0
    docker inspect \
      --format='backend state={{.State.Status}} exit={{.State.ExitCode}} oom={{.State.OOMKilled}} error={{json .State.Error}}' \
      "$failed_backend_id" 2>/dev/null || true
    docker inspect \
      --format='{{range .State.Health.Log}}{{println "health exit=" .ExitCode " output=" (json .Output)}}{{end}}' \
      "$failed_backend_id" 2>/dev/null | tail -n 8 || true
  }

  if ! compose_for "$image_tag" up -d --wait --wait-timeout 180; then
    report_backend_health
    rollback
    return 1
  fi

  local service container_id running_image expected_image
  for service in backend frontend; do
    container_id=$(docker compose "${compose_files[@]}" ps -q "$service")
    running_image=$(docker inspect --format='{{.Config.Image}}' "$container_id")
    expected_image="ghcr.io/snipertecoficial/dipzee-${service}:$image_tag"
    if [[ "$running_image" != "$expected_image" ]]; then
      printf '%s did not start the expected release image.\n' "$service" >&2
      rollback
      return 1
    fi
  done
  docker image prune -f >/dev/null
  printf 'Release containers activated at %s.\n' "$image_tag"
}

rollback_release() {
  local run_id=${1:-}
  [[ "$run_id" =~ ^[0-9]+$ ]] || die "invalid workflow run id"
  local state_file="/tmp/dipzee-rollback-${run_id}"
  [[ -f "$state_file" && ! -L "$state_file" ]] || die "rollback state is unavailable"
  local tags
  mapfile -t tags < "$state_file"
  [[ "${#tags[@]}" -eq 2 ]] || die "rollback state is invalid"
  [[ "${tags[0]}" == "rollback-${run_id}" && "${tags[1]}" == "rollback-${run_id}" ]] \
    || die "rollback tags are invalid"
  compose_tags "${tags[0]}" "${tags[1]}" up -d --pull never --wait --wait-timeout 180
  printf 'Previous production image IDs restored.\n'
}

finalize() {
  local run_id=${1:-}
  [[ "$run_id" =~ ^[0-9]+$ ]] || die "invalid workflow run id"
  local state_file="/tmp/dipzee-rollback-${run_id}"
  rm -f -- "$state_file"
  docker image rm \
    "ghcr.io/snipertecoficial/dipzee-backend:rollback-${run_id}" \
    "ghcr.io/snipertecoficial/dipzee-frontend:rollback-${run_id}" \
    >/dev/null 2>&1 || true
}

case "${1:-}" in
  prepare)
    shift
    prepare "$@"
    ;;
  cleanup)
    shift
    cleanup "$@"
    ;;
  activate)
    shift
    activate "$@"
    ;;
  rollback)
    shift
    rollback_release "$@"
    ;;
  finalize)
    shift
    finalize "$@"
    ;;
  *)
    die "usage: remote_deploy.sh {prepare|cleanup|activate|rollback|finalize} ..."
    ;;
esac
