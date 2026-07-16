# PLAT-01 — Create Kyverance Simplified repository and foundation

> Status: Complete

## Delivery record

- Remote: https://github.com/maharatha/kyverance-simplified
- Branch: `codex/plat-01-foundation`
- Draft PR: not opened — GitHub defaulted the new repo to the only pushed branch (`codex/plat-01-foundation`), so head and base were identical; creating an empty `main` base was declined by policy. CI also runs on `codex/**` pushes.

## Outcome

Create the new remote Git repository named `kyverance-simplified` and establish a clean application scaffold using the approved Kyverance technology baseline. Bring the documentation in this workspace into the repository and implement CI parity. Do not deploy or modify production infrastructure in this task.

## Read first

- `docs/README.md`, `03-system-architecture.md`, `07-azure-github-transition.md`, `08-master-delivery-roadmap.md`.
- Original: `C:\SourceCode\kyverance\CONTRIBUTING.md`, `.github/workflows/ci.yml`, `frontend/package.json`, `backend/pyproject.toml`, `backend/Dockerfile`, and `infrastructure/docker-compose.yml`.

## Scope

- Create the remote repository under the authenticated GitHub account/organization, named exactly `kyverance-simplified`, and clone/init it at `C:\SourceCode\kyverance-simplified` without overwriting the approved docs.
- Create the modular-monolith folder layout in `03-system-architecture.md` with minimal runnable Next.js/TypeScript and FastAPI/Python application shells.
- Add local Postgres/Redis development compose configuration, secure `.env.example` files without real credentials, backend test setup, frontend lint/test/build setup, Dockerfile(s), and CI equivalent to the original test/build guarantees.
- Commit and push the initial foundation to a `codex/` branch; open a draft PR only if repository policy/tools allow it.

## Constraints

- Preserve the stated runtime choices and versions where compatible; do not copy source application code, secrets, databases, or production configuration wholesale.
- Do not provision Azure resources, alter DNS, edit existing Kyverance workflows/resources, deploy, configure Entra, or create production credentials.
- CI must run backend tests with Postgres/Redis and a clean frontend production build.
- Keep documentation source-of-truth in `docs/`; record deviations as ADRs.

## Verification

- Fresh local setup works from documented commands.
- Backend test command, frontend lint/test/build, and Docker build(s) pass.
- GitHub Actions CI is present and valid.
- Report repository URL, branch/PR, changed files, exact checks/results, dependencies, and unresolved setup risks.
