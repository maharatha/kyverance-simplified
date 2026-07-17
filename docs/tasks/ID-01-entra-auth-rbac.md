# ID-01 — Implement Entra authentication, RBAC, and protected shell

> Status: Implemented on `codex/id-01-entra-rbac`

## Read first

1. `docs/README.md`
2. `docs/03-system-architecture.md`
3. `docs/04-identity-rbac-and-plaid.md`
4. `docs/09-entra-auth-rbac-implementation.md`
5. Original read-only references: `C:\SourceCode\kyverance\frontend\auth.ts`, `auth.config.ts`, `middleware.ts`, `backend\src\kyverance\auth`, `backend\src\kyverance\api`, `docs\operations\DEVOPS.md`, and `docs\entra-branding\README.md`.

## Implement

Implement all approved scope in `09-entra-auth-rbac-implementation.md`. Preserve the existing Next.js/FastAPI/project conventions. Keep Home UX intact and replace fixture-only identity only at the boundary needed to render authenticated vs signed-out state. Add focused migrations, API and frontend tests.

## Constraints

- Start from the current `codex/web-01-home` branch but create a focused `codex/id-01-entra-rbac` branch before committing.
- Do not create/alter Entra, Azure, GitHub secrets, Key Vault, DNS, deployment workflows, Plaid, or any database outside the local/new simplified schema.
- Do not copy original credentials or tenant IDs into code, docs, test fixtures, screenshots, or logs.
- Use a local explicit development mode only; it must be impossible for a browser caller to turn it on in non-local environments.
- Never use a model/agent for authorization.

## Verification

Run backend tests (including new auth/authorization coverage), frontend lint/tests/production build, migration upgrade/downgrade checks where supported, and local signed-out/development-auth smoke checks. Record all actual commands/results and screenshots under `docs/tasks/id-01-evidence/`.

## Final report

Report branch/commit, changed files, migration impact, exact checks/results, configuration variables required for later Entra provisioning, local test credentials only if non-secret fixtures, security risks, and remaining operational prerequisites. Commit and push only when all local gates pass.
