# AGENT-01 — Agent registry, facts packets, and proposal contracts

Implement the first bounded AI-agent platform foundation using the existing Kyverance Simplified stack and conventions. Read `docs/01-product-foundation.md`, `docs/06-ai-agents-and-background-jobs.md`, and `docs/08-master-delivery-roadmap.md` before coding.

## Outcome

Members can create multiple private agent configurations for portfolios and generate deterministic, evidence-grounded proposal records from authorized portfolio facts. This task establishes contracts, persistence, policy, and a simple review UI; it does not call an external AI provider yet.

## Backend

- Add persisted agent registry entities scoped to owner and portfolio. Include name, purpose/capabilities, lifecycle state, model provider/name/version placeholders, prompt-template version, budget limits, created/updated timestamps, and audit-safe metadata.
- Add immutable facts-packet records containing portfolio/version reference, data-as-of time, authorized evidence references, normalized holdings/cash/risk inputs, and a stable checksum.
- Add immutable agent proposal/forecast records with agent identity, facts checksum, proposal type, horizon, assumptions, structured actions/draft allocation, evidence references, confidence and limitations, safety decision, cost/latency placeholders, status, and timestamps.
- Enforce object-level ownership. An agent cannot access another member's private portfolio, facts, or proposals.
- Enforce the product invariant: agents can draft proposals but cannot confirm, submit, schedule, or execute orders. No endpoint may mutate the ledger or order state.
- Use strict request/response schemas, bounded field sizes, idempotency where generation records are created, and audit events for agent/facts/proposal creation and lifecycle changes.
- Provide migrations and deterministic fixture-mode behavior consistent with the repository's existing testing approach.

## Frontend

- Add a restrained portfolio-level Agent workspace that lists agents and proposals and supports creating an agent configuration and generating/reviewing a deterministic fixture proposal.
- Clearly label every proposal as a simulation scenario, show data-as-of time, evidence, assumptions, horizon, uncertainty/limitations, model/version placeholder, safety result, and a deliberate `Review proposal` action.
- Never show an `Execute`, `Auto-trade`, or misleading certainty action. A proposal may link to the existing simulated order preview flow only as a separate future/manual step; do not implement that link in this task.
- Include loading, empty, error, permission-denied, and unavailable states; maintain the existing simple visual system and responsive/accessibility behavior.

## Tests and verification

- Backend tests: ownership isolation, immutable facts/proposals, checksum stability, validation, idempotency, audit events, and proof that proposal APIs cannot execute or mutate orders/ledger.
- Frontend tests: empty/list/review states, required forecast disclosures, permission/error handling, and absence of execution/auto-trade controls.
- Run the full backend and frontend suites plus relevant build/lint checks.
- Verify the local authenticated portfolio Agent workspace and API routes without changing Azure, Entra, Plaid, CI/CD, DNS, secrets, production data, or the original Kyverance repository.

## Delivery

Work only on AGENT-01 and preserve unrelated user files. Commit and push the bounded implementation to the current branch. The final report must list changed files, migrations, tests/build results, local route/API verification, security/invariant checks, commit hash, push result, and any genuine remaining limitations.
