# Product Foundation — Kyverance Simplified

## Product decision

Kyverance Simplified is where investors and AI agents build, test, explain, fork, and share simulated portfolios. The product makes the investment process visible: thesis, evidence, scenario, risk, simulated execution, outcome, and subsequent changes.

It is not a brokerage, signal-selling black box, or copy-trading network.

## The core objects

| Object | Meaning |
| --- | --- |
| Portfolio | An owner-controlled simulated strategy workspace with holdings, cash, thesis, rules and history. A member can own many. |
| Portfolio version | An immutable snapshot of holdings, strategy text, agent configuration and relevant data context at a point in time. |
| Fork | A new portfolio initialized from a public/shared portfolio version. It has an explicit source and license and diverges independently. |
| Agent | A bounded software collaborator. It can research, draft a portfolio, run scenarios, explain a change and propose a simulated action; it cannot execute without the owner’s explicit confirmation. |
| Forecast | An agent-generated scenario, never a promise. It is versioned, grounded and time-bound. |
| Creator offering | Permissioned access to research, portfolio versions, discussion or fork rights. It is not payment for trading signals or execution. |

## First implementation milestone: Home

The first shipped screen is a calm, AI-forward Home page. It is the intentional entrypoint after sign-in, not a complete terminal.

### Home audiences

| State | Primary action | Supporting content |
| --- | --- | --- |
| Signed out | `Explore portfolios` / `Create your first portfolio` | Clear simulation and AI-agent value proposition; sign-in entry. |
| New member | `Create a portfolio` | Short three-step onboarding; no empty analytics wall. |
| Member with portfolio | `Review your agent brief` or `Continue portfolio` | Portfolio value/provenance/data status, one agent insight, one next action. |
| Creator | `Publish a version` | Creator portfolio health, draft/published state and a small community signal. |
| Agent-enabled member | `Review agent proposal` | A proposal card with evidence, assumptions, forecast horizon and a deliberate review CTA. |

### Home layout rules

1. The top area contains one clear message and one primary action.
2. The personal portfolio summary is truthful even when market data or AI is unavailable.
3. Agent output is secondary to deterministic facts and visibly labeled as a scenario/proposal.
4. Discovery is a small, curated strip; there is no infinite feed or return-first ranking.
5. The screen has complete loading, empty, error, signed-out and permission-denied states.
6. Mobile preserves the same hierarchy and never hides essential disclosures behind hover.

## Roles and permissions (design target)

| Role | Initial authority |
| --- | --- |
| Member | Own portfolios, simulate trades, create private agents, fork only where permitted, manage private Plaid connections. |
| Creator | Member authority plus publish portfolios/versions and create approved creator offerings. |
| Moderator | Review reports and moderate public/community content; cannot access private portfolios by default. |
| Support | Limited, audited support access; no portfolio mutation or secret access. |
| Finance operations | Payment/refund administration only after marketplace scope is approved; no content moderation or trading authority. |
| Administrator | Minimal, audited platform configuration; cannot bypass immutable source records. |
| Agent service identity | Scoped service authority only; no direct user impersonation, trading confirmation, payment, or public publishing authority. |

All portfolio operations also require object-level policy: owner, explicitly granted collaborator, entitled subscriber, public viewer, or moderator as applicable.

## Initial delivery sequence

| ID | Document then Cursor task | Outcome |
| --- | --- | --- |
| FND-01 | Information architecture + Home UX | Approved screen spec, visual system and responsive/state behavior. |
| WEB-01 | Home page shell | New Home page and design primitives using static/fixture data only; no auth or financial mutation. |
| ID-01 | Identity/RBAC design | Entra CIAM/Auth.js integration, role model, authorization contract and audit events. |
| ID-02 | Authentication implementation | Sign-in/out, profile bootstrap and role-safe application shell. |
| DATA-01 | Plaid read-only design | Consent, token handling, refresh, disconnect/deletion, and data-source separation. |
| DATA-02 | Plaid implementation | Private, read-only account/holding connection. |
| SIM-01 | Simulation domain and multiple portfolios | Canonical portfolio/wallet/order model and migrations. |
| FORK-01 | Portfolio version/fork design | Source lineage, license, entitlement and divergence rules. |
| AGENT-01 | Agent platform design | Agent registry, facts packets, forecast schema, evaluations and cost controls. |
| MKT-01 | Creator marketplace design | Entitlements, payment policy, moderation and legal gates. |
| OPS-01 | Azure cutover design | New repository CI/CD, resource transition, verification and rollback. |

## Cursor review contract

For each row, Codex will first create one task document. Cursor receives only that task and its listed source documents. After Cursor reports, Codex checks: scope discipline; visual simplicity; authorization; financial/agent invariants; migrations; automated tests; accessibility; CI; and Azure/rollback impact. A failing gate means a corrective task, not the next feature.

## Hard rules

- All simulated orders require a human confirmation after a deterministic preview. Agents may draft but never confirm.
- Every forecast/AI insight names the data as-of time, evidence, assumptions, uncertainty and model/version.
- Forks are independent and never subscribe to, synchronize with, or execute the source portfolio’s future trades.
- Public performance always carries provenance and risk context; users cannot claim broker verification without verified evidence.
- Plaid data is private/read-only by default and cannot flow into creator pages without a separate, explicit consent and policy decision.
- Any payment or marketplace rollout requires a dedicated legal, security, privacy and abuse-review gate.
