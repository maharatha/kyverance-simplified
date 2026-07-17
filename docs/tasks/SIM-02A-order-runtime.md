# SIM-02A — Repair simulated-order runtime

> Status: Implemented on `codex/sim-02-order-loop`

## Outcome

Repair the SIM-02 no-config/runtime regression: Home and Portfolio workspace must return HTTP 200 with fixture quote mode; retain explicit preview/confirmation/idempotency/decimal rules. Diagnose the 500, add regression tests/evidence, run checks, commit/push focused fix only. No infrastructure, real trading, Plaid, secrets, or scope expansion.

## Result

- **Root cause:** Codex acceptance probed a concurrent Next.js `dev` server on `:3001` whose `.next` cache was corrupted (RSC/webpack manifest / pack ENOENT errors), producing intermittent Home/Portfolio HTTP 500s — the same class of failure documented in DATA-01A. Separately, SIM-02 loaded portfolio detail via `Promise.all(portfolio, positions, activity)`, so a missing/stale order route or unmigrated SIM-02 tables blanked the whole workspace even when wallet/ledger were healthy.
- **Fix:** Soft-fail positions/activity on the portfolio detail client; return empty HTTP 200 lists from positions/activity when order tables are missing; keep fixture-only quote mode fail-closed (`503` for non-fixture).
- Evidence: `docs/tasks/sim-02-evidence/sim-02a-runtime-smoke.txt`
