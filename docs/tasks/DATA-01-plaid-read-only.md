# DATA-01 — Plaid read-only connection foundation

> Status: Implemented (local fake-provider verification; no live Plaid credentials required)

## Outcome

Implement the private, read-only Plaid foundation: secure server-side Link-token creation/exchange boundaries, encrypted/token-reference-ready connection storage, consent lifecycle, account/holding provenance model, disconnect/deletion workflow, and a minimal Connected Accounts settings surface. No real Plaid credentials or production connection is required for local verification.

## Read first

- `docs/04-identity-rbac-and-plaid.md`, `docs/05-simulation-forks-and-community.md`, `docs/09-entra-auth-rbac-implementation.md`.
- Original read-only references: `C:\SourceCode\kyverance\frontend\lib\*plaid*`, `C:\SourceCode\kyverance\backend\src\kyverance\connectors`, relevant models/routes/tests.

## Constraints

- Read-only; private by default; no funding, orders, public sharing, creator use, or simulation linkage.
- Tokens/credentials stay server-side and are never logged, returned to a client, or committed. Use local fake provider/test mode when no credential is configured.
- Require authenticated owner and object-level authorization for every connection/account/holding action.
- Add migrations, audit events, consent/disconnect/deletion records, API/frontend tests and useful empty/error/configuration states.
- Do not create or modify Plaid, Azure, Entra, Key Vault, GitHub secrets, deployment, DNS, or original Kyverance resources.

## Verification

Run backend tests, frontend lint/tests/production build, migration checks, and local fake-provider smoke evidence. Commit/push a focused `codex/data-01-plaid-readonly` branch only after gates pass.
