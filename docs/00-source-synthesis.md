# Source Synthesis — Kyverance to Kyverance Simplified

## Purpose

This document turns the original Kyverance corpus into deliberate inputs for the new product. It prevents a clean rewrite from losing the difficult work already done and prevents legacy scope from quietly defining the new experience.

## Primary documents read in full

- `docs/README.md` — authority order and normative language.
- `docs/product/00-product-vision.md` — calm, specific, honest financial UX.
- `docs/ai/00-ai-architecture.md` and `AI_COACH_AND_GUARDRAILS.md` — deterministic facts before AI, grounded outputs, safety and evaluation.
- `docs/release-a/02-home-portfolio-read-models.md` and `04-thesis-order-loop.md` — one primary action, data freshness, canonical simulated order loop.
- `docs/architecture/TRADING_ENGINE.md` and `docs/data/DOMAIN_MODEL.md` — decimal, idempotency, atomic ledger and reconciliation invariants.
- `docs/security/SECURITY_MODEL.md` — object-level authorization, audit, privacy, AI and community abuse controls.
- `docs/portfolio-network/00-product-vision.md` through `06-ai-analysis.md`, and `09-ui-ux-principles.md` — multiple portfolios, publishing consent, provenance, snapshots, social boundaries, read-only clone, community and trust controls.
- `docs/operations/DEVOPS.md` and `docs/entra-branding/README.md` — the deployed Azure topology, CI/CD, Entra External ID/Auth.js and existing branding constraints.
- `docs/research/README.md` — canonical research, final-mile personalization, cache, jobs and cost-control design.
- `docs/engineering/CODEX_HANDOFF_PROTOCOL.md` — docs-first, bounded Cursor delivery and review gates.

The remaining documentation has been inventoried by area and will be consulted as each implementation document is authored. The product, data, architecture, AI, security, operations, release, and portfolio-network sets are authoritative inputs; betting and legacy playground materials are not default scope.

## Carry forward unchanged

| Original idea | Simplified decision |
| --- | --- |
| AI explains and reasons; deterministic systems calculate and enforce | Keep as a hard architecture rule. |
| Simulation ledger/execution/position source records | Keep as the only simulated-trading authority. |
| Database decimals, transactions, idempotency, receipts and reconciliation | Keep as non-negotiable broker-grade integrity. |
| Multiple portfolios, visibility, consent, provenance and immutable snapshots | Make these central product primitives. |
| Public profile, follows, discussions, reports, moderation and audit | Carry forward with creator-marketplace policy gates. |
| Facts packet, schema validation, evidence references and AI fallback | Make this the agent contract for every portfolio analysis/forecast. |
| Next.js/FastAPI/Postgres/Redis modular monolith | Keep it; do not introduce microservices in the first releases. |
| Entra CIAM/Auth.js, Key Vault, ACA/Jobs, ACR, SWA and GitHub Actions OIDC | Preserve the operating model during the Azure cutover. |

## Redesign for the new product

| Original design | Kyverance Simplified design |
| --- | --- |
| Read-only clone with no holdings | **Fork** creates a new owner-controlled simulated portfolio from an immutable source snapshot and strategy/agent configuration. It records source, version, license, and divergence; it never mirrors future trades. |
| AI coach educates but does not predict | An agent can create a **scenario forecast** and draft a portfolio. Every forecast includes time horizon, assumptions, evidence, uncertainty/confidence, model/provider/version, generation time, cost and disclosure. It remains non-executing. |
| Community focus on educational value without payment | Community gains a creator layer: paid access can unlock research, template versions, private discussion, or fork entitlement. It cannot buy prominence, guarantee return, or trigger copying/execution. |
| Trust score | Use transparent, versioned reputation signals based on process quality, provenance, history length, risk disclosure, and community/moderation status—not raw return alone. |
| Home as a personal portfolio read model | Home becomes a focused launchpad: one next action, personal portfolio state, agent briefing, and a limited curated discovery strip. |

## Explicitly excluded from the initial rewrite

- Live brokerage order routing or automated brokerage execution.
- Trade mirroring, automatic rebalance/copy execution, deposits, withdrawals, transfers, cash prizes or redemption.
- AI claims of guaranteed outcomes, invisible reasoning, ungrounded price claims, or agents with payment/trade authority.
- Betting, public return-only leaderboards, paid boosts, and engagement mechanics that bury risk context.

## Design ideas adopted

1. **Calm before clever:** a portfolio should be understandable before a chart, feed, or agent panel appears.
2. **Provenance before performance:** show simulated/live-import status, as-of timestamp, history length, benchmark and risk context near every performance claim.
3. **One clear next step:** Home should not be a dense trading terminal. Advanced tools stay contextual.
4. **Forks are lineage:** portfolio origin and meaningful changes are first-class, like Git commit history—not a shallow copy button.
5. **Agents show their work:** facts/evidence, assumptions, uncertainty and model identity are visible; raw hidden reasoning is not.
6. **Creators earn trust through process:** public history, thesis quality, risk transparency and traceability matter more than short-term gains.

## Key decisions requiring human/legal approval before release

- Creator pricing, subscriptions, refunds, tax/jurisdiction handling, and whether paid access is allowed in each launch geography.
- Market-data licensing and whether creator displays may use delayed/EOD data.
- Rules for bringing a third-party model/API key, including provider allowlist, data sharing and cost responsibility.
- Whether any imported Plaid holdings can be displayed publicly; default must be private and read-only.
