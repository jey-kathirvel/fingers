# Fingers

Social Media Engineering & Engagement platform for `https://fingers.ads-ai.in`.

## Stack

- **Frontend:** Next.js 14 + Tailwind (port `3090`)
- **Backend:** FastAPI (port `8095`; `8090` is reserved by another app on this VPS)
- **Worker:** due-post publisher, engagement inbox sync, analytics sync
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
- **LinkedIn live**: OAuth connect + Posts API publish when `LINKEDIN_CLIENT_ID` / `LINKEDIN_CLIENT_SECRET` are set
- Meta/Instagram: simulation only for now (live Meta deferred)

## Phase 4

- Unified engagement inbox (comments, messages, mentions, reviews)
- Classification: sentiment, intent, priority, lead probability
- AI reply suggestions with **Approve & Send**
- Inbox sync (simulation feed for connected accounts; worker refreshes periodically)

## Phase 5

- Normalized account and post metrics
- Analytics trends, platform breakdown, top posts
- Dashboard KPIs fed from synced metrics
- Metrics sync endpoint + worker refresh

## Phase 6

- Campaign planning with objectives, platforms, KPIs and content links
- Leads mini-CRM pipeline: new → contacted → interested → demo → proposal → converted/lost
- Convert inbox interactions into attributed leads

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
