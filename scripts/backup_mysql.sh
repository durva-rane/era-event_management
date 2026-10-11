#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ -f "$ROOT_DIR/.env" ]]; then
  set -a
  # .env is trusted local configuration, never a file from an upload or request.
  source "$ROOT_DIR/.env"
  set +a
fi

DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-3306}"
DB_USER="${DB_USER:-era_user}"
DB_NAME="${DB_NAME:-era_db}"
BACKUP_DIR="${BACKUP_DIR:-$ROOT_DIR/backups/mysql}"
BACKUP_RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-14}"
MYSQLDUMP_BIN="${MYSQLDUMP_BIN:-mysqldump}"
MYSQL_BIN="${MYSQL_BIN:-mysql}"

if [[ ! "$DB_NAME" =~ ^[A-Za-z0-9_]+$ ]]; then echo "Invalid DB_NAME." >&2; exit 2; fi
if ! [[ "$BACKUP_RETENTION_DAYS" =~ ^[0-9]+$ ]] || (( BACKUP_RETENTION_DAYS < 1 )); then echo "BACKUP_RETENTION_DAYS must be a positive integer." >&2; exit 2; fi
mkdir -p "$BACKUP_DIR"
chmod 700 "$BACKUP_DIR"
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
target="$BACKUP_DIR/${DB_NAME}_${stamp}.sql.gz"
tmp="$target.tmp.$$"
trap 'rm -f "$tmp"' EXIT

export MYSQL_PWD="${DB_PASSWORD:-}"
"$MYSQLDUMP_BIN" --host="$DB_HOST" --port="$DB_PORT" --user="$DB_USER" \
  --single-transaction --routines --triggers --events --hex-blob --default-character-set=utf8mb4 \
  "$DB_NAME" | gzip -c > "$tmp"
gzip -t "$tmp"
mv "$tmp" "$target"
chmod 600 "$target"
find "$BACKUP_DIR" -maxdepth 1 -type f -name "${DB_NAME}_*.sql.gz" -mtime "+$BACKUP_RETENTION_DAYS" -delete
echo "MySQL backup created: $target"
