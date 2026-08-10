#!/usr/bin/env bash
# Install/refresh Fingers on the VPS at /opt/fingers
set -euo pipefail

APP_ROOT="${APP_ROOT:-/opt/fingers}"
REPO_SRC="${REPO_SRC:-$(cd "$(dirname "$0")/.." && pwd)}"

echo "Deploying from ${REPO_SRC} -> ${APP_ROOT}"
mkdir -p "${APP_ROOT}"/{logs,storage}

# Preserve local secrets across syncs
ENV_BAK=""
if [[ -f "${APP_ROOT}/.env" ]]; then
  ENV_BAK=$(mktemp)
  cp "${APP_ROOT}/.env" "${ENV_BAK}"
fi

rsync -a --delete \
  --exclude '.git' \
  --exclude '.env' \
  --exclude '.env.created_credentials' \
  --exclude 'frontend/node_modules' \
  --exclude 'frontend/.next' \
  --exclude 'backend/.venv' \
  --exclude '.venv' \
  --exclude '__pycache__' \
  --exclude 'storage/backups' \
  "${REPO_SRC}/" "${APP_ROOT}/"

if [[ -n "${ENV_BAK}" ]]; then
  cp "${ENV_BAK}" "${APP_ROOT}/.env"
  rm -f "${ENV_BAK}"
  chmod 600 "${APP_ROOT}/.env"
fi

if [[ ! -f "${APP_ROOT}/.env" ]]; then
  echo "Missing ${APP_ROOT}/.env" >&2
  exit 1
fi

set -a
# shellcheck disable=SC1091
source "${APP_ROOT}/.env"
set +a

python3 -m venv "${APP_ROOT}/backend/.venv"
# shellcheck disable=SC1091
source "${APP_ROOT}/backend/.venv/bin/activate"
pip install -q --upgrade pip
pip install -q -r "${APP_ROOT}/backend/requirements.txt"
# Ensure sqlite driver for local tests if needed
pip install -q pysqlite3-binary 2>/dev/null || true

cd "${APP_ROOT}/backend"
export PYTHONPATH="${APP_ROOT}/backend"
alembic upgrade head
python -m app.db.seed

cd "${APP_ROOT}/frontend"
if ! command -v npm >/dev/null; then
  echo "npm missing" >&2
  exit 1
fi
npm ci
API_INTERNAL_URL=http://127.0.0.1:8095 npm run build

install -m 644 "${APP_ROOT}/scripts/systemd/fingers-api.service" /etc/systemd/system/fingers-api.service
install -m 644 "${APP_ROOT}/scripts/systemd/fingers-web.service" /etc/systemd/system/fingers-web.service
install -m 644 "${APP_ROOT}/scripts/systemd/fingers-worker.service" /etc/systemd/system/fingers-worker.service
systemctl daemon-reload
systemctl enable fingers-api fingers-web fingers-worker
systemctl restart fingers-api fingers-web fingers-worker

echo "Deploy complete"
systemctl --no-pager --full status fingers-api fingers-web fingers-worker | sed -n '1,80p'
