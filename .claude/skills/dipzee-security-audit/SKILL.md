---
name: dipzee-security-audit
description: Audit Dipzee for multi-tenancy leaks, IDOR, auth bypass, or general security issues before launch or after adding a new route/feature. Use when asked to review security, check multi-tenancy isolation, or verify a new endpoint is safe.
---

# Dipzee security audit

Dipzee is a FastAPI + MongoDB + React SaaS (stock screener) that charges
real money via Stripe. It is **not** a Supabase-style app — the frontend
never talks to the database directly, only to the FastAPI backend, which
does its own authorization on every route. Keep that architectural fact in
mind: most "vibe coding" vulnerability classes (exposed anon key, missing
Row Level Security) structurally don't apply here. The real risk surface is
IDOR-style bugs in hand-written route handlers, not a misconfigured DB
policy.

## Checklist for every route (existing or new)

1. **Auth dependency present and correct**: regular user routes use
   `Depends(get_current_user)`; anything admin-only uses
   `Depends(get_superadmin)` (defined in `backend/security.py`, wraps
   `get_current_user` + `role == "superadmin"`). A route with no
   `Depends(...)` at all is a bug unless it's explicitly meant to be
   public (e.g. `/health`, `/billing/config`, `/webhook/stripe`).
2. **Every DB query/mutation is scoped to `user["id"]` from the JWT**,
   never to a client-supplied id from the URL/body. Grep for
   `db.<collection>.find_one`/`update_one`/`delete_one` in the route file
   and check the filter dict includes the authenticated user's own id, not
   a path/query param the caller controls.
3. **Ownership checks on anything looked up by an opaque id** (e.g. a
   Stripe session id, an alert id): fetch the record, then explicitly
   compare its owner field to `user["id"]` and 403 on mismatch. Don't
   assume "the id is hard to guess" is a substitute for this.
4. **Timing side channels on auth-adjacent endpoints**: login/password
   reset/email-check flows must do the same amount of work (e.g. pay the
   full bcrypt cost) whether or not the account exists, using a
   precomputed dummy hash — see `_DUMMY_PASSWORD_HASH` in
   `backend/routes_auth.py` for the existing pattern. An `or` that
   short-circuits before the password check is the classic way this
   silently regresses.
5. **Refresh token invariants** (`backend/refresh_tokens.py`): rotation and
   revocation always look up by the *hash* of the raw token, never by a
   client-supplied user id; reuse of an already-rotated token triggers
   `revoke_all()` for that user.

## LLM/AI feature checklist

Dipzee's AI Virtual Analyst (`backend/routes_ai.py`) feeds third-party
content (news headlines) into an LLM prompt — this is Dipzee's one real
indirect-prompt-injection surface. When touching this or adding a new
LLM-integrated feature:

- Any untrusted/third-party text going into a prompt should have an
  explicit system-prompt instruction to treat it as data, not instructions.
- Any field the LLM is expected to return from a fixed enum (like
  `stance`) must be validated server-side against that enum, not trusted
  as-is — don't rely on the frontend's fallback rendering as the only
  safety net.
- Check whether the LLM output is cached per-ticker/global vs per-user —
  a shared cache means a successful manipulation affects every user who
  hits that cache key, not just one session, which raises the severity of
  an otherwise-contained finding.
- Confirm nothing renders LLM output via `dangerouslySetInnerHTML` — plain
  React text interpolation (`{value}`) auto-escapes and is the reason a
  manipulated LLM response can't become stored XSS here.

## Supporting infra already in place (verify, don't rebuild)

- `backend/url_safety.py` — SSRF guard (`socket.getaddrinfo` +
  `ipaddress`) blocking private/loopback/link-local targets; applied at
  both save-time and delivery-time for anything that fetches a
  user-supplied URL.
- `backend/mongo-init/init-app-user.js` — least-privilege Mongo user
  (`dipzee_app`, `readWrite` on the app DB only, distinct from the root
  cluster user the backend never connects as).
- `backend/login_guard.py` — per-email (not per-IP) brute-force lockout,
  5 fails / 10 min; separate from the per-IP `RateLimitMiddleware` in
  `backend/security_middleware.py`.

## How to run a full pass efficiently

For a broad audit (not a single-route check), split the work by concern
across parallel Explore agents rather than reading every route file
serially: one agent for IDOR across all routes, one for admin-route gating,
one for session/token isolation. Report back with concrete `file:line`
citations for anything found — vague findings aren't actionable.
