# ID-01A — Repair local Auth.js runtime and Edge boundary

> Status: Implemented on `codex/id-01-entra-rbac`

## Outcome

Repair the post-ID-01 runtime regression: with no Entra credentials configured, `GET /` and `/sign-in` must render the signed-out/local development experience instead of returning HTTP 500. Preserve production fail-closed behavior for protected routes and avoid importing Node-only Auth.js/Jose functionality into Edge middleware where possible.

## Scope

- Diagnose the actual local 500 from the current ID-01 branch.
- Make missing Entra configuration a safe signed-out state for public pages; do not invent credentials or silently enable development identity in production.
- Split edge-safe route gating/configuration from Node Auth.js functionality as required by Next.js/Auth.js conventions.
- Resolve the production-build Edge Runtime warning when feasible; if a documented upstream warning remains, prove it does not break runtime and record the exact reason.
- Add regression tests and update task evidence.

## Verification

- `GET /` and `/sign-in` return HTTP 200 with no Entra credentials.
- Protected UI/API behavior remains neutral 401/redirect as documented.
- Backend tests, frontend lint/tests/production build pass.
- Commit/push a focused corrective commit; do not change Azure, Entra, secrets, deployments, Plaid, or unrelated product scope.

## Result

- **Root cause:** Auth.js `MissingSecret` when `AUTH_SECRET` was unset and Edge middleware imported `next-auth`, causing `/api/auth/session` HTTP 500 (and noisy middleware failures on every request).
- **Fix:** Edge cookie-only route gate (no Auth.js/Jose), Node-only jwt/session callbacks in `auth.ts`, non-production local `AUTH_SECRET` fallback, production still fail-closed without a secret.
- **Edge warning:** Resolved — production middleware is 34.1 kB with no jose Edge Runtime warning.
- Evidence: `docs/tasks/id-01-evidence/id-01a-runtime-smoke.txt`
