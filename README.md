# Fingers

Social Media Engineering & Engagement platform for `https://fingers.ads-ai.in`.

## Stack

- **Frontend:** Next.js 14 + Tailwind (port `3090`)
- **Backend:** FastAPI (port `8095`; `8090` is reserved by another app on this VPS)
- **Worker:** due-post publisher with retries every ~20s
- **Database:** PostgreSQL (`fingers_db`)

## Phase 1

- Auth (login/logout/session token)
- Organizations + memberships
- Brands CRUD + active brand switcher
- RBAC roles: admin, creator, reviewer, approver, analyst
- Dashboard shell fed by `/api/analytics/overview`
- Health/version endpoints
- systemd services + Apache reverse proxy deployment

## Phase 2

- AI Content Studio (generate / rewrite / ideas)
- Platform-neutral content items + channel versions
- Draft → review → approved workflow
- Media asset library (prompt/reference records)
- OpenRouter (preferred) or OpenAI when API keys are set; otherwise local Social Media Engineer engine

## Phase 3

- Social account connect (simulation or live token)
- Schedule posts + calendar view
- Publish now / retry / cancel
- Worker processes due posts with idempotency + publishing logs
- Meta + LinkedIn adapters (simulation by default; live Graph/API stubs until OAuth credentials are wired)

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
uvicorn app.main:app --reload --port 8095

# frontend
cd ../frontend
npm install
API_INTERNAL_URL=http://127.0.0.1:8095 npm run dev -- --port 3090
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
- Integrations: `GET /api/integration-health`
