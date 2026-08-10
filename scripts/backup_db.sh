#!/usr/bin/env bash
set -euo pipefail

# Daily PostgreSQL backup for Fingers.
# Cron example: 15 2 * * * /opt/fingers/scripts/backup_db.sh

APP_ROOT="${APP_ROOT:-/opt/fingers}"
BACKUP_DIR="${BACKUP_DIR:-/opt/fingers/storage/backups}"
KEEP_DAYS="${KEEP_DAYS:-14}"

set -a
source "${APP_ROOT}/.env"
set +a

mkdir -p "${BACKUP_DIR}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUT="${BACKUP_DIR}/fingers_db_${STAMP}.sql.gz"

# Extract DB name from DATABASE_URL
DB_NAME="$(python3 - <<'PY'
import os
from urllib.parse import urlparse
u=urlparse(os.environ['DATABASE_URL'].replace('postgresql+psycopg','postgresql'))
print(u.path.lstrip('/'))
PY
)"

sudo -u postgres pg_dump "${DB_NAME}" | gzip > "${OUT}"
find "${BACKUP_DIR}" -type f -name 'fingers_db_*.sql.gz' -mtime +"${KEEP_DAYS}" -delete
echo "Backup written: ${OUT}"
