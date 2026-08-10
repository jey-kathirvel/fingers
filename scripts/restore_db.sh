#!/usr/bin/env bash
set -euo pipefail

# Restore procedure (document + smoke helper)
# Usage: bash scripts/restore_db.sh /opt/fingers/storage/backups/fingers_db_XXXX.sql.gz

BACKUP_FILE="${1:-}"
APP_ROOT="${APP_ROOT:-/opt/fingers}"

if [[ -z "${BACKUP_FILE}" || ! -f "${BACKUP_FILE}" ]]; then
  echo "Usage: $0 /path/to/fingers_db_XXXX.sql.gz"
  exit 1
fi

set -a
source "${APP_ROOT}/.env"
set +a

DB_NAME="$(python3 - <<'PY'
import os
from urllib.parse import urlparse
u=urlparse(os.environ['DATABASE_URL'].replace('postgresql+psycopg','postgresql'))
print(u.path.lstrip('/'))
PY
)"

systemctl stop fingers-api fingers-worker || true
sudo -u postgres psql -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='${DB_NAME}' AND pid <> pg_backend_pid();" || true
sudo -u postgres dropdb --if-exists "${DB_NAME}"
sudo -u postgres createdb "${DB_NAME}"
gunzip -c "${BACKUP_FILE}" | sudo -u postgres psql "${DB_NAME}"
systemctl start fingers-api fingers-worker || true
echo "Restore complete from ${BACKUP_FILE}"
