$ErrorActionPreference = 'Stop'

$cursorCommand = Join-Path $env:LOCALAPPDATA 'cursor-agent\cursor-agent.cmd'
$workspace = 'C:\SourceCode\kyverance-simplified'
$taskPrompt = @'
Implement only FORK-01 at C:\SourceCode\kyverance-simplified\docs\tasks\FORK-01-versioned-portfolios.md.

Read first (authoritative for Simplified product):
- docs/tasks/FORK-01-versioned-portfolios.md
- docs/05-simulation-forks-and-community.md
- docs/01-product-foundation.md (Portfolio version / Fork definitions and hard rules)
- docs/03-system-architecture.md (portfolios module; append-only versions)
- docs/00-source-synthesis.md (fork vs original read-only clone distinction)
- Existing SIM-01/SIM-02 portfolio/ledger/order code under backend/src/kyverance/portfolios, simulation, api/routes, and frontend portfolios UI

Also read original Kyverance portfolio-network docs for publishing/consent/snapshot/provenance patterns (do NOT copy read-only clones as the fork model):
- C:\SourceCode\kyverance\docs\portfolio-network\00-product-vision.md
- C:\SourceCode\kyverance\docs\portfolio-network\01-architecture-principles.md
- C:\SourceCode\kyverance\docs\portfolio-network\02-domain-model.md
- C:\SourceCode\kyverance\docs\portfolio-network\03-portfolio-service.md
- C:\SourceCode\kyverance\docs\portfolio-network\09-ui-ux-principles.md

Outcome:
- Immutable portfolio versions that snapshot metadata, thesis/rules, holdings/allocation, optional agent-config reference, data context, and checksum
- Publish flow with explicit consent, visibility choice, provenance, license/disclosure
- Fork from exactly one permitted public version into a new owner-controlled simulated portfolio with durable source lineage (source portfolio/version, license/entitlement, timestamp) and independent wallet/positions
- No automatic sync, mirrored trades, public sharing by default, creator payment, Plaid exposure, or real trading
- API + minimal UI + tests + Alembic migrations
- After checks pass: commit and push on focused branch `codex/fork-01-versioned-portfolios` (branch from current SIM-02 tip)

Product distinction (critical):
- Original portfolio-network "read-only clone" has no holdings/orders — Simplified FORK-01 fork is an independent simulated portfolio that diverges after creation
- Do not implement discovery feeds, follows, comments, trust scores, marketplace/payments, agents execution, or FORK-02 extras

Constraints:
- Keep scope exact to FORK-01 only
- No external infrastructure, Azure/Entra/DNS/secrets changes, original Kyverance code edits, real trading, Plaid into public/fork surfaces, payments, or scope expansion
- Preserve repository conventions (decimal strings, object auth, Idempotency-Key, append-only source records, private-by-default)

Verification:
- Backend unit/API tests for version immutability, publish consent, fork lineage, independent wallet, authz denials
- Frontend tests for version/publish/fork UX surfaces added
- Run the same backend/frontend test and production build gates used by prior SIM tasks
- Leave brief evidence under docs/tasks/fork-01-evidence/ if useful

Final report must include: changed files, checks/results, migration/rollout impact, risks, branch/commit, and push status.
'@

Write-Host 'Starting Cursor FORK-01 versioned-portfolios session...' -ForegroundColor Cyan
& $cursorCommand -p --trust --auto-review --stream-partial-output --output-format stream-json --workspace $workspace $taskPrompt
Write-Host 'Cursor session ended. Codex will review the final report and verification.' -ForegroundColor Yellow
