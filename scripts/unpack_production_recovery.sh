#!/usr/bin/env bash
set -Eeuo pipefail

die() {
  printf 'recovery error: %s\n' "$*" >&2
  exit 1
}

artifact=${1:-}
deploy_key=${2:-}
output_dir=${3:-}
[[ -f "$artifact" && ! -L "$artifact" ]] || die "artifact must be a regular file"
[[ -f "$deploy_key" && ! -L "$deploy_key" ]] || die "deploy key must be a regular file"
[[ -n "$output_dir" && ! -e "$output_dir" ]] || die "output directory must not already exist"

umask 077
mkdir -m 700 -- "$output_dir"
temp_dir=$(mktemp -d)
cleanup() {
  rm -f -- "$temp_dir/passphrase" "$temp_dir/bundle.tar"
  rmdir -- "$temp_dir" 2>/dev/null || true
}
trap cleanup EXIT

python3 -c 'import sys; raw=open(sys.argv[1], "rb").read().replace(b"\r\n", b"\n").strip(); sys.stdout.buffer.write(b"dipzee-production-recovery-v1\0" + raw)' "$deploy_key" \
  | sha256sum | awk '{print $1}' > "$temp_dir/passphrase"
gpg --batch --yes --pinentry-mode loopback --passphrase-file "$temp_dir/passphrase" \
  --output "$temp_dir/bundle.tar" --decrypt "$artifact"

mapfile -t entries < <(tar -tf "$temp_dir/bundle.tar")
[[ "${#entries[@]}" -eq 3 ]] || die "unexpected recovery bundle contents"
backup_file=${entries[0]}
[[ "$backup_file" =~ ^dipzee-backup-[0-9]{8}T[0-9]{12}Z[.]json[.]gz[.]enc$ ]] \
  || die "invalid backup filename"
[[ "${entries[1]}" == "recovery-key" && "${entries[2]}" == "manifest.txt" ]] \
  || die "unexpected recovery bundle paths"
tar --no-same-owner --no-same-permissions -xf "$temp_dir/bundle.tar" -C "$output_dir"
chmod 600 "$output_dir/$backup_file" "$output_dir/recovery-key" "$output_dir/manifest.txt"

format=$(sed -n 's/^format=//p' "$output_dir/manifest.txt")
expected_sha=$(sed -n 's/^backup_sha256=//p' "$output_dir/manifest.txt")
expected_bytes=$(sed -n 's/^backup_bytes=//p' "$output_dir/manifest.txt")
[[ "$format" == "dipzee-production-recovery-v1" ]] || die "unsupported recovery format"
[[ "$expected_sha" =~ ^[0-9a-f]{64}$ ]] || die "invalid manifest digest"
[[ "$expected_bytes" =~ ^[1-9][0-9]*$ ]] || die "invalid manifest size"
[[ "$(sha256sum "$output_dir/$backup_file" | awk '{print $1}')" == "$expected_sha" ]] \
  || die "backup digest mismatch"
[[ "$(wc -c < "$output_dir/$backup_file" | tr -d '[:space:]')" == "$expected_bytes" ]] \
  || die "backup size mismatch"
python3 -c 'import base64,sys; value=open(sys.argv[1], encoding="ascii").read(); assert len(base64.b64decode(value, validate=True)) == 32' \
  "$output_dir/recovery-key"

printf 'Recovery bundle authenticated and unpacked to %s. Keep this directory private.\n' "$output_dir"
