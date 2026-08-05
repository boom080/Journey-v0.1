#!/bin/sh
set -eu

: "${DATABASE_URL:?Set DATABASE_URL to the staging PostgreSQL connection string}"

output_dir="${BACKUP_DIR:-artifacts/staging/backups}"
mkdir -p "$output_dir"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
output="$output_dir/journey-staging-$timestamp.dump"

docker run --rm -e DATABASE_URL postgres:18.4-alpine \
  sh -c 'pg_dump --format=custom --no-owner --no-acl "$DATABASE_URL"' > "$output"
shasum -a 256 "$output" > "$output.sha256"
printf 'backup=%s\nchecksum=%s.sha256\n' "$output" "$output"
