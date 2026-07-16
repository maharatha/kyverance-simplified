# Kyverance Simplified — Product and Delivery Blueprint

> Status: discovery complete; PLAT-01 foundation scaffold complete locally.  
> Repository: `kyverance-simplified` (this workspace).  
> Source material: `C:\SourceCode\kyverance\docs` (181 documents reviewed as an indexed corpus; the documents listed in `00-source-synthesis.md` were read in full and are the primary design inputs).

Kyverance Simplified is an AI-native community for simulated portfolios. People create and practise with portfolios, inspect their process, fork public work, collaborate with agents, and sell access to research and portfolio templates. It never sends an order to a brokerage in the initial releases.

## Read in this order

1. [Source synthesis](00-source-synthesis.md) — what is inherited, redesigned, and excluded from the original Kyverance.
2. [Product foundation](01-product-foundation.md) — product decision, boundaries, and the first release sequence.
3. Subsequent documents, written and approved one at a time: information architecture and home-page UX; identity/RBAC; Plaid; simulation; forks; agents; creator marketplace; Azure cutover.
4. A single task document for each Cursor implementation slice. No task is handed to Cursor until its parent design document is approved.

## Documentation-to-delivery rule

Every implementation task must state its outcome, scope, exclusions, acceptance criteria, verification, authorization/data/AI constraints, rollout impact, and rollback. Cursor implements one task at a time; Codex reviews the diff, tests, UX evidence, and Azure impact before the next task begins.

## Non-negotiable technical baseline

- Next.js 15, React 19, TypeScript; FastAPI, Pydantic, SQLAlchemy, PostgreSQL, Redis, Alembic, Python 3.12.
- Microsoft Entra External ID / Auth.js authentication; Azure Key Vault for secrets.
- Azure Container Apps, Container Apps Jobs, ACR, Static Web Apps, Blob Storage, GitHub Actions OIDC deployment.
- Fixed-decimal quantities/money, transactional idempotent financial mutations, immutable source records, auditable derived views.

## Product boundary

The platform is simulation and education first. Agents can produce attributed, evidence-backed scenario forecasts and draft portfolios; deterministic services enforce all calculations, permissions, and simulated executions. A paid creator product sells access to portfolio research, templates, and controlled fork rights—not automated or mirrored trading.
