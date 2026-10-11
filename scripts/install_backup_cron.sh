#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="${BACKUP_LOG_DIR:-$SCRIPT_DIR/../logs}"
mkdir -p "$LOG_DIR"
CRON_LINE="10 2 * * * $SCRIPT_DIR/backup_mysql.sh >> $LOG_DIR/mysql-backup.log 2>&1"
(crontab -l 2>/dev/null | grep -Fv "$SCRIPT_DIR/backup_mysql.sh" || true; echo "$CRON_LINE") | crontab -
echo "Installed daily MySQL backup at 02:10 local server time."
