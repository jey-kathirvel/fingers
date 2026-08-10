#!/usr/bin/env bash
# Daily PostgreSQL backup for fingers_db
set -euo pipefail
APP_ROOT="${APP_ROOT:-/opt/fingers}"
BACKUP_DIR="${BACKUP_DIR:-/opt/fingers/storage/backups}"
mkdir -p "${BACKUP_DIR}"
# shellcheck disable=SC1091
source "${APP_ROOT}/.env"
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
FILE="${BACKUP_DIR}/fingers_db_${STAMP}.sql.gz"
# DATABASE_URL=postgresql+psycopg2://user:pass@host:5432/db
URL="${DATABASE_URL#postgresql+psycopg2://}"
CREDS="${URL%%@*}"
HOSTDB="${URL#*@}"
USER="${CREDS%%:*}"
PASS="${CREDS#*:}"
HOSTPORT="${HOSTDB%%/*}"
DB="${HOSTDB#*/}"
HOST="${HOSTPORT%%:*}"
PORT="${HOSTPORT##*:}"
export PGPASSWORD="${PASS}"
pg_dump -h "${HOST}" -p "${PORT}" -U "${USER}" "${DB}" | gzip > "${FILE}"
find "${BACKUP_DIR}" -name 'fingers_db_*.sql.gz' -mtime +14 -delete
echo "Backup written: ${FILE}"
