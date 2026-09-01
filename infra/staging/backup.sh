#!/bin/sh
set -eu

# No connection URL in shell arguments; use a verified Compose container.
: "${BACKUP_CONTAINER:?Set the exact Journey database container name}"
: "${BACKUP_PROJECT:?Set its Journey Compose project name}"
: "${BACKUP_DATABASE:?Set the exact database name}"
: "${BACKUP_USER:?Set the database user}"
: "${BACKUP_DIR:?Set an absolute private backup directory}"
: "${BACKUP_KEY_FILE:?Set a separate private 32-byte key file}"
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec node "$script_dir/../privacy/backup.mjs" backup \
  --container "$BACKUP_CONTAINER" --project "$BACKUP_PROJECT" \
  --database "$BACKUP_DATABASE" --user "$BACKUP_USER" \
  --directory "$BACKUP_DIR" --key-file "$BACKUP_KEY_FILE"
