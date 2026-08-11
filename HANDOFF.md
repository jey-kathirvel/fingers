# Fingers — Handoff Document

**Date:** 2026-08-11  
**Product URL:** https://fingers.ads-ai.in  
**Repo:** https://github.com/jey-kathirvel/fingers  
**Plan:** `Fingers_Social_Media_Engineering_Implementation_Plan_87e1.pdf`  
**Live version:** `0.8.0` (Alembic head `0008`)

---

## 1. Status summary

| Item | State |
|------|--------|
| Plan phases 1–8 | **Complete** and merged to `main` |
| Open PRs | **None** |
| VPS deploy | Live at `/opt/fingers`, services active |
| LinkedIn live | Configured (OAuth + Posts API) |
| Meta (IG/FB) live | **Deferred** — simulation only |
| Redis | Configured in `.env` but **unavailable** on host (app still runs) |

`main` tip at handoff: `5c684c6` (merge of PR #10).

---

## 2. What shipped (by phase)

| Phase | Version | PR | Capability |
|------|---------|-----|------------|
| 1 Foundation | — | #1/#2 | Auth, orgs, brands, RBAC, shell, deploy |
| 2 AI Studio | — | #3 | Generate/rewrite/ideas, content versions, assets, OpenRouter |
| 3 Publishing | 0.3.x | #4 | Accounts, calendar, schedule, worker, logs |
| LinkedIn live | — | #5 | OAuth connect + live publish |
| 4 Engagement | 0.4.0 | #6 | Unified inbox, classify, AI reply Approve & Send |
| 5 Analytics | 0.5.0 | #7 | Account/post metrics, trends, KPIs |
| 6 Campaigns & Leads | 0.6.0 | #8 | Campaigns, content links, lead pipeline, convert inbox→lead |
| 7 AI Advisor | 0.7.0 | #9 | Rule (+ optional LLM) recommendations from metrics/inbox/leads |
| 8 Automation & Listening | **0.8.0** | #10 | Automation rules/runs, listening terms/mentions, SOV |

---

## 3. Architecture (quick map)

```
Browser → Apache (fingers.ads-ai.in)
            ├─ /        → Next.js (127.0.0.1:3090)
            └─ /api     → FastAPI (127.0.0.1:8095)

Worker (fingers-worker):
  - publish due posts
  - sync simulated inbox
  - run automations
  - sync listening mentions
  - sync analytics
```

**Stack**
- Frontend: Next.js 14 + Tailwind (`frontend/`)
- Backend: FastAPI + SQLAlchemy + Alembic (`backend/`)
- DB: PostgreSQL `fingers_db` / user `fingers_user`
- Worker: `worker/main.py` via systemd

**Do not use port 8090** — reserved by another app (SimplPay) on the shared Hostinger VPS. Fingers uses **8095** (API) and **3090** (web). Do not edit booking/SimplPay Apache defaults.

---

## 4. VPS layout & services

| Path / unit | Purpose |
|-------------|---------|
| `/opt/fingers` | App root |
| `/opt/fingers/.env` | Secrets (mode 600; never rsync-overwrite blindly) |
| `/opt/fingers/backend/.venv` | Python venv |
| `fingers-api` | uvicorn `app.main:app` on `127.0.0.1:8095` |
| `fingers-web` | Next.js on `127.0.0.1:3090` |
| `fingers-worker` | Background loop (~20s) |

Useful scripts under `scripts/`:
- `deploy.sh` — rsync-safe deploy, migrate, build, restart
- `provision-db.sh` — DB bootstrap
- `configure-apache.sh` — reverse proxy
- `backup-db.sh` — DB backup
- `systemd/*.service` — unit files

---

## 5. Deploy / ops cheatsheet

```bash
# From a machine with SSH to the VPS (password auth via FINGERS_SSH_* secrets)
export SSHPASS="$FINGERS_SSH_PRIVATE_KEY"   # note: secret holds password, not a key file
RSYNC_SSH='sshpass -e ssh -o StrictHostKeyChecking=no -o PreferredAuthentications=password -o PubkeyAuthentication=no'

# Prefer full-tree sync (do NOT multi-source rsync — it flattens layout)
rsync -az --delete \
  --exclude '.git' --exclude '.env' --exclude 'frontend/node_modules' \
  --exclude 'frontend/.next' --exclude 'backend/.venv' --exclude '__pycache__' \
  -e "$RSYNC_SSH" \
  ./ root@${FINGERS_SSH_HOST}:/opt/fingers/

# On VPS
source /opt/fingers/.env && export DATABASE_URL
cd /opt/fingers/backend
.venv/bin/alembic upgrade head
systemctl restart fingers-api fingers-web fingers-worker
cd /opt/fingers/frontend && API_INTERNAL_URL=http://127.0.0.1:8095 npm run build
systemctl restart fingers-web
```

Or run `/opt/fingers/scripts/deploy.sh` on the VPS after code is synced.

**Settings use `lru_cache`** — restart `fingers-api` after any `.env` change.

**Bump version:** set `APP_VERSION` in `/opt/fingers/.env` (overrides `app_version` default in code).

---

## 6. Auth & tenancy

- Seed admin: `SEED_ADMIN_EMAIL` / `SEED_ADMIN_PASSWORD` in `.env` (see `.env.example`)
- JWT in `Authorization: Bearer …`
- Org scope via `X-Organization-Id`
- Roles: `admin`, `creator`, `reviewer`, `approver`, `analyst`

---

## 7. Integrations

| Platform | Mode | Notes |
|----------|------|--------|
| LinkedIn | **Live** when `LINKEDIN_CLIENT_ID` / `LINKEDIN_CLIENT_SECRET` set | Redirect: `https://fingers.ads-ai.in/api/integrations/linkedin/callback` |
| Instagram / Facebook | **Simulation only** | Meta live deferred; empty `META_APP_*` is expected |
| YouTube / X | Planned | Shown as `planned` in integration-health |
| OpenRouter | Live | Preferred LLM for Studio / Advisor refine |
| Redis | Optional | Health may show `unavailable`; not required for current worker loop |

---

## 8. Key API surfaces

| Area | Prefix |
|------|--------|
| Auth / orgs / brands | `/api/auth/*`, `/api/organizations/*`, `/api/brands/*` |
| Studio / content / assets | `/api/ai/*`, `/api/content/*`, `/api/assets/*` |
| Publishing | `/api/social-accounts/*`, `/api/publishing/*`, `/api/integrations/*` |
| Engagement | `/api/inbox/*`, `/api/interactions/*` |
| Analytics | `/api/analytics/*` |
| Campaigns / leads | `/api/campaigns/*`, `/api/leads/*` |
| Advisor | `/api/advisor/*` |
| Automations | `/api/automations/*` |
| Listening | `/api/listening/*` |
| Health | `/api/health`, `/api/version`, `/api/integration-health` |

Migrations: `backend/alembic/versions/0001` … `0008_phase8_automation_listening.py`.

---

## 9. Frontend routes

Dashboard, Studio, Publishing, Engagement, Analytics, Campaigns, Leads, Advisor, Automations, Listening, Brands, Assets, Integrations, Settings, Login.

No remaining “Coming Soon” phase placeholders for phases 1–8.

---

## 10. What’s still pending (not a plan Phase 9)

These are **follow-ups / hardening**, not unfinished roadmap phases:

1. **Live Meta (Instagram/Facebook)** — OAuth + Graph publish/inbox (largest MVP gap vs plan).
2. **Redis** — install/start Redis on VPS or point `REDIS_URL` at a working instance.
3. **YouTube / X adapters** — currently `planned` only.
4. **Real social listening** — Phase 8 uses **simulated** mentions; wire platform APIs where permitted.
5. **Audit UI / full `/api/audit`** — stub returns empty list; `audit_logs` table is written by automations/publishing paths.
6. **Settings depth** — profile/role display only; no team invite / secret management UI.
7. **Recurring report delivery** — automation notifies in-app; no email/Slack report schedule yet.

---

## 11. Hard constraints (do not break)

- Shared VPS with other products — **never bind to 8090**; do not alter unrelated Apache vhosts.
- Keep app under `/opt/fingers`.
- Never commit or rsync-overwrite production `.env`.
- Prefer simulation adapters when live credentials are missing; fail closed with clear messages.

---

## 12. Local development

```bash
cp .env.example .env
cd backend && python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export PYTHONPATH=.
alembic upgrade head && python -m app.db.seed
uvicorn app.main:app --reload --port 8095

cd ../frontend && npm install
API_INTERNAL_URL=http://127.0.0.1:8095 npm run dev -- --port 3090
```

Tests: `cd backend && PYTHONPATH=. pytest -q`

---

## 13. Suggested next work order

1. Meta live credentials + adapter (publish + inbox sync) for Instagram/Facebook.  
2. Stand up Redis (or remove dependency from health expectations).  
3. Replace listening simulation with real mention sources where APIs allow.  
4. Audit log browser + richer Settings (members/invites).  
5. Optional: YouTube/X once Meta path is proven.

---

## 14. Contacts / secrets location

- Production secrets: `/opt/fingers/.env` on VPS only.  
- Cloud agent SSH: `FINGERS_SSH_HOST`, `FINGERS_SSH_PRIVATE_KEY` (password via `sshpass`, despite the name).  
- Template: repo `.env.example` (no production secrets).

---

*End of handoff. Phases 1–8 complete on `main` @ 0.8.0.*
