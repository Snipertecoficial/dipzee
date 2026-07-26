# Dipzee

Stock-screener SaaS. Assigns every stock a transparent 0–100 **Opportunity
Score** (from price position, upside to analyst targets, and dividend yield),
with watchlists, real-time alerts, a market screener, portfolio tracking, and an
AI Virtual Analyst. FastAPI + MongoDB backend, React (CRACO) frontend, 4
languages (en/pt/es/fr).

---

## Architecture

```
Browser ─► Traefik (edge, TLS)  ─►  Caddy  ─┬─ /api/* ─► backend (FastAPI, :8000)
   (shared VPS)                              └─ else   ─► frontend (nginx static)
                                                             backend ─► MongoDB
```

- **backend/** — FastAPI app. Routers per feature (`routes_*.py`), shared services
  (`*_service.py`), Stripe billing (`routes_billing.py`), APScheduler jobs
  (`scheduler.py`), scoped Mongo access (`database.py`, non-root `dipzee_app` user).
- **frontend/** — React SPA, i18next, design tokens in `src/index.css`, per-route
  meta via react-helmet-async.
- **Caddy** does the `/api/*` vs static split; **Traefik** (shared with another
  project on the VPS) terminates TLS — see comments in `docker-compose.yml`.

## Local development

```bash
cp .env.example .env        # fill in values (dev values are fine locally)
docker compose up --build   # builds from source; app on http://localhost:80
```

`docker compose` (base file) builds images locally. Production uses pre-built
images instead — see Deploy.

## Environment

All config is via `.env` (never committed). `.env.example` documents every
variable. The launch-critical ones:

| Var | Needed for | If unset |
|---|---|---|
| `ENV=production`, `DOMAIN`, `CORS_ORIGINS`, `REACT_APP_BACKEND_URL` | prod correctness | dev-mode / broken routing |
| `JWT_SECRET` (strong) | auth | prod refuses to boot |
| `MONGO_*`, `SUPERADMIN_*` | DB + admin | no admin seeded |
| `STRIPE_*` | payments | billing 503s |
| `RESEND_API_KEY` + `RESEND_FROM_EMAIL` | password-reset & alert emails | reset silently can't send (logged ERROR) |
| `ANTHROPIC_API_KEY` (or Gemini/OpenAI) | AI analyst | AI tab 503s |
| `TELEGRAM_BOT_TOKEN` | Telegram alerts | channel hidden in UI |
| `SENTRY_DSN` | error tracking | no-op |
| `BACKUP_S3_*` | offsite backups | local-only backups (still run) |

⚠️ **Don't set `SUPERADMIN_EMAIL`/`SUPERADMIN_PASSWORD` once real admin accounts
exist** — `seed_superadmin()` runs every boot and would overwrite the password.

## Deploy (CI builds, VPS pulls)

Push to `main` → GitHub Actions (`.github/workflows/deploy.yml`):
1. **build-and-push**: builds both images, runs the pytest suite inside the
   backend image (a red test blocks deploy), pushes to GHCR.
2. **deploy**: SSHes to the VPS, `git reset --hard origin/main`, then
   `docker compose -f docker-compose.yml -f docker-compose.prod.yml pull && up -d`.
   The VPS never builds (avoids OOM on the small host). Health is verified
   against `HEALTHCHECK_URL` before the run is called done.

**Rollback:** re-run the workflow on an earlier commit (Actions → Run workflow),
or on the VPS pin the previous image tag (`ghcr.io/…/dipzee-backend:<sha>`) and
`up -d`.

## Database backup & restore

A gzipped snapshot of all non-cache collections is written **daily (03:30 ET)**
to the `backup_data` Docker volume (`/data/backups`), keeping the last
`BACKUP_KEEP` (default 7). This survives redeploys. If `BACKUP_S3_*` is set it is
**also** uploaded offsite (any S3-compatible store; free tiers on Backblaze B2 /
Cloudflare R2 are large enough).

- **On demand:** admin panel → or `POST /api/admin/backup/run`; list via
  `GET /api/admin/backup/status`.
- **Restore** (upsert by `_id`, idempotent):
  ```bash
  docker compose -f docker-compose.yml -f docker-compose.prod.yml \
    exec backend python scripts/restore_backup.py /data/backups/<snapshot>.json.gz
  ```
- The whole-VPS-loss case is additionally covered by the offsite copy and by
  Hostinger's own VPS snapshots (hPanel).

## Monitoring

- **Readiness:** `GET /api/health` (unauthenticated) checks DB + scheduler,
  returns 503 when degraded. Point an external uptime monitor (UptimeRobot,
  Better Stack — free tiers) at it.
- **Admin health:** `GET /api/admin/health` (superadmin) — DB latency, scheduler,
  real email capability, key presence, provider.
- **Errors:** set `SENTRY_DSN` for backend error tracking.
- Container healthchecks are defined for mongo and backend in `docker-compose.yml`.

## Market data (commercial note)

`yfinance` is the built-in fallback but is **not licensed for commercial
redistribution**. Set a licensed provider key (`FMP_API_KEY`, `FINNHUB_API_KEY`,
…) before charging users; the resilient cascade in `backend/providers.py` /
`market_service.py` uses it automatically. See `backend/market_service.py` for
the honest per-feature coverage note.

## Testing

```bash
docker compose exec backend python -m pytest tests/ -q
```
The same suite runs in CI before every deploy.
