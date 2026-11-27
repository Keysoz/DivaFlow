#!/bin/bash
# Restore a Diva Store backup folder (PROD-05).
#
# Usage: /opt/diva/restore.sh /path/to/backup-folder
# The folder is the one produced by `install.ps1 -Action Backup`: it contains
# the database dump and the public/private file archives.

set -euo pipefail

SRC="${1:?usage: restore.sh /path/to/backup-folder}"

if [ ! -d "$SRC" ]; then
    echo "Backup folder not found: $SRC" >&2
    exit 1
fi

DB="$(ls "$SRC"/*database.sql.gz 2>/dev/null | head -1 || true)"
if [ -z "$DB" ]; then
    echo "No *database.sql.gz found in $SRC" >&2
    exit 1
fi

FILES="$(ls "$SRC"/*files.tar 2>/dev/null | head -1 || true)"
PRIVATE="$(ls "$SRC"/*private-files.tar 2>/dev/null | head -1 || true)"

ARGS=(--force)
if [ -n "$FILES" ]; then
    FILES_NAME="$(basename "$FILES")"
    ARGS+=(--with-public-files "/restore/$FILES_NAME")
fi
if [ -n "$PRIVATE" ]; then
    PRIVATE_NAME="$(basename "$PRIVATE")"
    ARGS+=(--with-private-files "/restore/$PRIVATE_NAME")
fi

cd /opt/diva
DB_NAME="$(basename "$DB")"
exec docker compose --env-file .env -f store.prod.yml run --rm --no-deps \
    -v "$SRC":/restore \
    backend bench --site diva.local restore "/restore/$DB_NAME" "${ARGS[@]}"
