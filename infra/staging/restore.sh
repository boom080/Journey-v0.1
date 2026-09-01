#!/bin/sh
set -eu

# Never overwrite or expose a live database. This wrapper only validates an
# isolated restore, drops old Agent state/consent and invalidates old sessions.
: "${RESTORE_FILE:?Set an authenticated .jbackup archive}"
: "${BACKUP_KEY_FILE:?Set the separate private key file}"
: "${RESTORE_REPORT:?Set an absolute private report path}"
if [ -n "${DATABASE_URL:-}" ]; then
  echo "Live DATABASE_URL restore is disabled; only an isolated drill is supported" >&2
  exit 2
fi
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec node "$script_dir/../privacy/backup.mjs" drill \
  --archive "$RESTORE_FILE" --key-file "$BACKUP_KEY_FILE" --report "$RESTORE_REPORT"
