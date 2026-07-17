# WEB-01 — Build the Home page shell

> Status: Implemented — awaiting Codex review.

## Outcome

Implement the reviewed Home page shell for Kyverance Simplified using static typed fixtures. The result must be a polished, responsive, accessible Next.js page that demonstrates every UX state in `docs/02-home-page-ux.md` without pretending that backend functionality exists.

## Read first

1. `docs/README.md`
2. `docs/00-source-synthesis.md`
3. `docs/01-product-foundation.md`
4. `docs/02-home-page-ux.md`
5. The new repository’s `README`, contributor instructions, frontend conventions, and package scripts.

## Scope

- Create the Next.js Home route and its page-local/components-local styling using existing repository conventions.
- Implement `HomeShell`, `HomeHero`, `PortfolioSnapshotCard`, `AgentProposalCard`, `NextStepCard`, `DiscoveryPreview`, and `DataStatus` or equivalents with clear ownership.
- Implement typed fixture data and a development-only state switch that is inaccessible in production builds, or a focused Story/test harness if that is the project convention.
- Add component tests for signed-out, new-member, active-member, creator, agent-proposal, and unavailable/error states.
- Add accessibility assertions appropriate to the repository test tooling.

## Constraints

- Preserve Next.js 15, React 19, TypeScript, the existing lint/test/build conventions, and the dark Kyverance visual direction described in the UX document.
- Format money-like fixture values as supplied decimal strings. Do not calculate portfolio values, P&L, or agent confidence in the client.
- Agent content must state scenario/draft and “no trade placed” when it represents a proposal.
- Make one primary CTA visually dominant per state. Do not add a feed, leaderboard, live-price ticker, brokerage controls, payment controls, or charts that lack an accessible alternate.
- Do not add dependencies unless essential; explain and obtain approval before doing so.
- Do not create/modify Azure resources, GitHub Actions, secrets, deployment configuration, commits, or pull requests.

## Acceptance criteria

- All criteria in `docs/02-home-page-ux.md` pass.
- Routes and links are safe placeholders or existing routes—no broken navigation.
- At desktop and mobile widths, content order and disclosures match the document.
- Automated lint, component tests, and production build pass.
- Final report includes changed files, screenshots/state evidence, commands/results, dependency changes, and residual risks.

## Verification

Run the repository’s frontend lint, unit/component-test, and production-build commands. Capture visual evidence for signed-out, new-member, active-member, and mobile states. Report any environment/configuration blocker instead of working around it.

## Explicit exclusions

No auth, RBAC, API client, database, migrations, market data, simulation order action, Plaid, AI call, payment, deployment, or infrastructure change.
