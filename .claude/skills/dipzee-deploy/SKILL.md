---
name: dipzee-deploy
description: Ship a code change to the live Dipzee VPS and verify it actually deployed. Use whenever the user asks to deploy, push to production, "subir para a VPS", check if a deploy went out, or update the live site at dipzee.com.
---

# Dipzee deploy

Dipzee deploys via push-to-main, not manual VPS commands. There is no direct
shell/SSH access to the VPS from this environment — the only path to
production is a git push that GitHub Actions picks up.

## The pipeline

1. Push (or merge) to `main` triggers `.github/workflows/deploy.yml`.
2. CI sanity-checks first: `python3 -m compileall backend` and a throwaway
   `yarn build` of the frontend (dummy `REACT_APP_BACKEND_URL`, discarded —
   the real build happens on the VPS with the real URL).
3. SSH deploy step (plain OpenSSH, no marketplace action) runs on the VPS:
   `git fetch origin main && git reset --hard origin/main && docker compose
   up -d --build && docker image prune -f`.
4. Post-deploy health check: polls `HEALTHCHECK_URL` up to 15× (5s apart)
   until it gets HTTP 200 with `{"status": "ok"}`.

The VPS's deploy key is **read-only by design** — it can only pull, never
push. Any fix must originate here and go through git, never be hand-patched
on the VPS (a hand-patch is silently wiped by the next `git reset --hard`).

## Before pushing

1. Rebuild the affected service locally and confirm it compiles clean:
   `docker compose build backend` and/or `docker compose build frontend`.
   A clean `docker compose build` is the closest thing to what CI will do.
2. For backend changes touching a route: `docker compose up -d backend`,
   then sanity-check with `docker exec dipzee-backend-1 python -c "..."`
   (import the module, hit the endpoint) before trusting it.
3. For frontend changes: confirm `Compiled successfully` in the build
   output, not just that the container started.
4. Review `git status`/`git diff --stat` before staging — this repo has
   payment/credential-adjacent files (`.env`, `backups/`) that must never be
   committed; both are already gitignored, don't override that.

## After pushing

There is no local way to confirm the VPS actually updated — this repo has
no `gh` CLI installed in this environment. Either ask the user to check the
GitHub Actions "Deploy to VPS" run, or ask them to confirm the live site at
dipzee.com reflects the change.

## Infrastructure notes (don't re-derive these, they're already settled)

- **Traefik, not Caddy, owns ports 80/443 on the VPS.** This VPS also runs
  an unrelated "Areis Advogados" project through the same Traefik instance
  — never touch Traefik's own config, only Dipzee's `caddy` service labels
  in `docker-compose.yml`. The external Docker network Traefik watches is
  named `traefik` (confirmed against the live Areis config — not the more
  common `traefik_public` convention, which was an earlier wrong guess).
  Caddy itself just keeps doing the `/api/*` vs frontend path split
  (`Caddyfile`), now as plain HTTP behind Traefik's TLS termination.
- **Mongo**: the backend connects as the scoped `dipzee_app` user
  (`readWrite` on the app DB only), never the root user — `MONGO_URL` is
  built from `MONGO_APP_USER`/`MONGO_APP_PASSWORD` in `docker-compose.yml`.
- **Never set `SUPERADMIN_EMAIL`/`SUPERADMIN_PASSWORD` in the VPS `.env`**
  once real superadmin accounts exist in the database. `seed_superadmin()`
  runs on every backend startup and will silently overwrite the existing
  superadmin's password with whatever is in those env vars — this has
  already caused a real lockout once this project.
- Migrations (`backend/migrations/`) run on startup and are fail-fast
  (unlike other best-effort startup hooks) — a broken migration blocks
  the whole backend from coming up, which is intentional for a payments app.
