# AI Agents and Background Jobs

## Agent contract

Agents are product capabilities, not autonomous authorities. An agent may produce evidence-grounded research summaries, risk explanations, scenario forecasts, portfolio drafts, thesis drafts, comparisons and reflection prompts. Deterministic services own calculations and policies. The agent output is strict structured data validated against schemas and policy checks.

Every forecast/proposal persists: agent identity; model/provider/version; prompt-template version; authorized facts checksum; evidence references; generation time; horizon; assumptions; confidence/limitations; safety decision; cost/latency; and user feedback. It may never claim certainty, invent market facts, hide missing data, infer protected attributes, expose secrets, execute/schedule trades, or access unauthorized portfolios.

## Bring-your-own-model

Start with an allowlisted provider abstraction. BYOM is a later guarded release: encrypted credential storage, explicit data-sharing disclosure, per-user/project budgets, model allowlist, no direct tool escalation, capability scopes, audit logs, immediate revocation, and provider-specific abuse/retention review. Raw provider keys never enter browser/client logs or model context.

## Jobs preserved/rebuilt from original Kyverance

| Job | Responsibility | Target runtime |
| --- | --- | --- |
| Market scheduler/worker | calendar-aware EOD ingest, normalized quote publication, freshness/correction handling | ACA scheduled jobs |
| Research scheduler/worker | canonical evidence/research generation, artifact publication and cache invalidation | ACA scheduled jobs |
| Agent proposal worker | bounded async analysis/forecast generation; budget and safety validation | ACA job or queue consumer |
| Outbox worker | durable event delivery and projection updates | ACA job/worker |
| Reconciliation worker | ledger/position/value recomputation and incident creation | ACA scheduled job |
| Housekeeper | retention, consent/deletion queues, operational reports and cost checks | ACA scheduled job |

Each job has idempotency, a health/last-success signal, bounded retries, dead-letter/incident behavior, correlation IDs, logs/metrics, runbook, least-privilege identity, feature flag and a manual safe rerun. AI outages cannot block portfolio pages, simulation execution or reconciliation.

## Delivery order

First preserve market-data and research job contracts behind feature flags. Next add the agent facts-packet/proposal path. Then add agent scheduling only after evaluations, cost budgets, observability and a kill switch are proven.
