# Fingers

AI-first Social Media Engineering & Engagement platform for multi-brand teams.

Deployment target: `https://fingers.ads-ai.in` on Hostinger VPS (`/opt/fingers`).

## Phase 1 status (this PR)

Foundation only — no social platform API integrations yet:

- FastAPI backend with auth, organizations, brands, RBAC, health/version, dashboard overview API
- Next.js UI shell with login, brand switcher, dashboard, settings brand CRUD
- Alembic migration, Celery worker stub, systemd + Apache deploy assets
- Local SQLite-backed tests and VPS deploy/backup scripts

## Stack

| Layer | Choice |
| --- | --- |
| Frontend | Next.js + React + Tailwind |
| Backend | FastAPI |
| Database | PostgreSQL (SQLite for local tests) |
| Jobs | Redis + Celery |
| Deploy | systemd + Apache reverse proxy + Certbot |

## Repository layout

```text
/opt/fingers (prod) or repo root (dev)
├── backend/
├── frontend/
├── worker/
├── migrations/
├── scripts/
├── deploy/
├── storage/
├── logs/
├── .env
└── README.md
```

## Local development

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
cp .env.example .env   # or use committed local .env template values carefully

# API
export PYTHONPATH=backend
uvicorn app.main:app --reload --port 8090

# Web
cd frontend
npm install
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8090/api npm run dev -- --port 3090
```

Default local admin (from `.env`):

- Email: `admin@ads-ai.in`
- Password: `ChangeMe123!`

## Tests

```bash
source .venv/bin/activate
export PYTHONPATH=backend
pytest backend/tests -q
```

## Hostinger VPS deploy

Confirmed target:

- Domain: `fingers.ads-ai.in`
- Path: `/opt/fingers`
- DB: `fingers_db` / `fingers_user`
- Ports: API `8090`, Web `3090`

On the VPS as root (after DNS A record points to the server):

```bash
export INITIAL_ADMIN_EMAIL='your@email'
export INITIAL_ADMIN_PASSWORD='strong-password'
export CERTBOT_EMAIL='your@email'
bash scripts/deploy_vps.sh
```

Services:

- `fingers-api.service`
- `fingers-web.service`
- `fingers-worker.service`

Backup / restore:

```bash
bash scripts/backup_db.sh
bash scripts/restore_db.sh /opt/fingers/storage/backups/fingers_db_XXXX.sql.gz
```

## Roadmap after Phase 1

1. AI Content Studio
2. Publishing adapters (Meta + LinkedIn first)
3. Engagement inbox
4. Analytics → Campaigns/Leads → Advisor → Automation/Listening

## Security notes

- Never commit production `.env` or social OAuth tokens
- Prefer SSH keys for VPS access; rotate any password shared in chat
- RBAC is enforced in backend APIs, not only in the UI
