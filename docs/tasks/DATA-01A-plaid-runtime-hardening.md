# DATA-01A — Repair Plaid local runtime regression

> Status: Implemented on `codex/data-01-plaid-readonly`

## Outcome

Repair the DATA-01 runtime regression: with no Plaid configuration, Home and `/settings/connected-accounts` must return HTTP 200 and show a clear unavailable/configuration state. Diagnose the 500; retain private read-only boundaries; add regression coverage; run backend/frontend checks and production build; commit/push only the focused fix. Do not alter Plaid, Azure, Entra, secrets, deployment, DNS, original Kyverance, or product scope.

## Result

- **Root cause:** Codex acceptance probed `/settings/connected-accounts`, which did not exist (404 with a session cookie). Concurrent Next.js `.next` cache corruption during DATA-01 also produced intermittent Home/settings HTTP 500s unrelated to Plaid credentials.
- **Fix:** Canonical `/settings/connected-accounts` route (legacy `/settings/connected` redirects); unavailable provider outside local/test when Plaid is unset; overview returns HTTP 200 with `configuration_required` even if connector tables are missing; Connected Accounts UI shows a clear unavailable/configuration state.
- Evidence: `docs/tasks/data-01-evidence/data-01a-runtime-smoke.txt`
