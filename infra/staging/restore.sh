#!/bin/sh
set -eu

: "${DATABASE_URL:?Set DATABASE_URL to the staging PostgreSQL connection string}"
: "${RESTORE_FILE:?Set RESTORE_FILE to a .dump created by backup.sh}"

if [ "${RESTORE_CONFIRM:-}" != "journey-staging" ]; then
  echo "Refusing restore: set RESTORE_CONFIRM=journey-staging" >&2
  exit 2
fi
if [ ! -f "$RESTORE_FILE" ]; then
  echo "Restore file not found: $RESTORE_FILE" >&2
  exit 2
fi

shasum -a 256 -c "$RESTORE_FILE.sha256"
docker run --rm -i -e DATABASE_URL postgres:18.4-alpine \
  sh -c 'pg_restore --clean --if-exists --no-owner --no-acl --dbname "$DATABASE_URL"' \
  < "$RESTORE_FILE"
echo "staging restore completed"
