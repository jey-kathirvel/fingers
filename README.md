# Fingers

Social Media Engineering & Engagement platform for `https://fingers.ads-ai.in`.

## Stack

- **Frontend:** Next.js 14 + Tailwind (port `3090`)
- **Backend:** FastAPI (port `8095`; `8090` is reserved by another app on this VPS)
- **Worker:** heartbeat/scheduler placeholder
- **Database:** PostgreSQL (`fingers_db`)

## Phase 1 (this release)

- Auth (login/logout/session token)
- Organizations + memberships
- Brands CRUD + active brand switcher
- RBAC roles: admin, creator, reviewer, approver, analyst
- Dashboard shell fed by `/api/analytics/overview`
- Health/version endpoints
- systemd services + Apache reverse proxy deployment

Later phases (AI Studio, publishing adapters, inbox, analytics, automation) are scaffolded in navigation as upcoming modules.

## Local development

```bash
cp .env.example .env
# backend
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export PYTHONPATH=.
alembic upgrade head
python -m app.db.seed
uvicorn app.main:app --reload --port 8090

# frontend
cd ../frontend
npm install
API_INTERNAL_URL=http://127.0.0.1:8090 npm run dev -- --port 3090
```

Default seed admin (change in production):

- Email: `admin@fingers.ads-ai.in`
- Password: from `SEED_ADMIN_PASSWORD` in `.env`

## VPS deploy

```bash
export FINGERS_DB_PASS='...'
./scripts/provision-db.sh
# write /opt/fingers/.env from .env.example with production secrets
./scripts/deploy.sh
./scripts/configure-apache.sh
```

Services: `fingers-api`, `fingers-web`, `fingers-worker`.

Backup: `./scripts/backup-db.sh`

## Health

- API: `GET /api/health`
- Version: `GET /api/version`
