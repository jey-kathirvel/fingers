#!/usr/bin/env bash
set -euo pipefail

# Idempotent Hostinger VPS bootstrap for Fingers Phase 1.
# Usage (on VPS as root):
#   APP_REPO=https://github.com/jey-kathirvel/fingers.git bash scripts/deploy_vps.sh

APP_ROOT="${APP_ROOT:-/opt/fingers}"
APP_REPO="${APP_REPO:-https://github.com/jey-kathirvel/fingers.git}"
APP_BRANCH="${APP_BRANCH:-main}"
DB_NAME="${DB_NAME:-fingers_db}"
DB_USER="${DB_USER:-fingers_user}"
DB_PASS="${DB_PASS:-}"
DOMAIN="${DOMAIN:-fingers.ads-ai.in}"

if [[ -z "${DB_PASS}" ]]; then
  DB_PASS="$(openssl rand -base64 24 | tr -d '=+/' | cut -c1-24)"
fi

export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y \
  git curl ca-certificates build-essential \
  python3 python3-venv python3-pip \
  postgresql postgresql-contrib redis-server \
  apache2 certbot python3-certbot-apache \
  libapache2-mod-proxy-uwsgi

if ! command -v node >/dev/null 2>&1; then
  curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
  apt-get install -y nodejs
fi

systemctl enable --now postgresql redis-server apache2

sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname='${DB_USER}'" | grep -q 1 \
  || sudo -u postgres psql -c "CREATE USER ${DB_USER} WITH PASSWORD '${DB_PASS}';"
sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='${DB_NAME}'" | grep -q 1 \
  || sudo -u postgres psql -c "CREATE DATABASE ${DB_NAME} OWNER ${DB_USER};"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE ${DB_NAME} TO ${DB_USER};"

mkdir -p "${APP_ROOT}"
if [[ ! -d "${APP_ROOT}/.git" ]]; then
  git clone -b "${APP_BRANCH}" "${APP_REPO}" "${APP_ROOT}"
else
  cd "${APP_ROOT}"
  git fetch origin
  git checkout "${APP_BRANCH}"
  git pull --ff-only origin "${APP_BRANCH}"
fi

cd "${APP_ROOT}"
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r backend/requirements.txt

if [[ ! -f "${APP_ROOT}/.env" ]]; then
  SECRET_KEY="$(openssl rand -hex 32)"
  cat > "${APP_ROOT}/.env" <<EOF
ENVIRONMENT=production
SECRET_KEY=${SECRET_KEY}
DATABASE_URL=postgresql+psycopg://${DB_USER}:${DB_PASS}@localhost:5432/${DB_NAME}
REDIS_URL=redis://localhost:6379/0
CORS_ORIGINS=https://${DOMAIN}
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8090
INITIAL_ADMIN_EMAIL=${INITIAL_ADMIN_EMAIL:-admin@ads-ai.in}
INITIAL_ADMIN_PASSWORD=${INITIAL_ADMIN_PASSWORD:-ChangeMe123!}
INITIAL_ADMIN_NAME=Fingers Admin
INITIAL_ORG_NAME=Ads AI
INITIAL_BRAND_NAME=Fingers Demo
NEXT_PUBLIC_API_BASE_URL=https://${DOMAIN}/api
PORT=3090
EOF
  chmod 600 "${APP_ROOT}/.env"
fi

set -a
source "${APP_ROOT}/.env"
set +a

cd "${APP_ROOT}"
PYTHONPATH=backend alembic upgrade head || true
PYTHONPATH=backend python - <<'PY'
from dotenv import load_dotenv
load_dotenv('/opt/fingers/.env', override=True)
from app.core.config import get_settings
get_settings.cache_clear()
from app.services.bootstrap import init_db
init_db()
print('seed complete')
PY

cd "${APP_ROOT}/frontend"
npm ci || npm install
NEXT_PUBLIC_API_BASE_URL="https://${DOMAIN}/api" npm run build

install -m 644 deploy/systemd/fingers-api.service /etc/systemd/system/fingers-api.service
install -m 644 deploy/systemd/fingers-web.service /etc/systemd/system/fingers-web.service
install -m 644 deploy/systemd/fingers-worker.service /etc/systemd/system/fingers-worker.service
install -m 644 deploy/apache/fingers.ads-ai.in.conf /etc/apache2/sites-available/fingers.ads-ai.in.conf

a2enmod ssl proxy proxy_http headers rewrite
a2ensite fingers.ads-ai.in
systemctl daemon-reload
systemctl enable fingers-api fingers-web fingers-worker
systemctl restart fingers-api fingers-web fingers-worker
systemctl reload apache2

if [[ "${SKIP_CERTBOT:-0}" != "1" ]]; then
  certbot --apache -d "${DOMAIN}" --non-interactive --agree-tos -m "${CERTBOT_EMAIL:-admin@ads-ai.in}" --redirect || true
fi

chown -R www-data:www-data "${APP_ROOT}/storage" "${APP_ROOT}/logs" || true
echo "Deploy complete: https://${DOMAIN}"
echo "DB user ${DB_USER} password stored in ${APP_ROOT}/.env"
