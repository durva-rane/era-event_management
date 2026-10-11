#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ -f "$ROOT_DIR/.env" ]]; then set -a; source "$ROOT_DIR/.env"; set +a; fi
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-3306}"
DB_USER="${DB_USER:-era_user}"
DB_NAME="${DB_NAME:-era_db}"
MYSQL_BIN="${MYSQL_BIN:-mysql}"
ASSUME_YES=false
if [[ "${1:-}" == "--yes" ]]; then ASSUME_YES=true; shift; fi
BACKUP_FILE="${1:-}"
if [[ -z "$BACKUP_FILE" || ! -f "$BACKUP_FILE" ]]; then echo "Usage: $0 [--yes] BACKUP.sql.gz" >&2; exit 2; fi
if [[ ! "$DB_NAME" =~ ^[A-Za-z0-9_]+$ ]]; then echo "Invalid DB_NAME." >&2; exit 2; fi
gzip -t "$BACKUP_FILE"
if [[ "$ASSUME_YES" != true ]]; then
  echo "This will restore the backup into database '$DB_NAME'. Confirm by typing the database name:"
  read -r confirmation
  [[ "$confirmation" == "$DB_NAME" ]] || { echo "Restore cancelled." >&2; exit 1; }
fi
export MYSQL_PWD="${DB_PASSWORD:-}"
gzip -dc -- "$BACKUP_FILE" | "$MYSQL_BIN" --host="$DB_HOST" --port="$DB_PORT" --user="$DB_USER" --default-character-set=utf8mb4 "$DB_NAME"
echo "Restore completed into database '$DB_NAME'."
