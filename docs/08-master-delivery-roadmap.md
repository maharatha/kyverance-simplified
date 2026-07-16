# Master Delivery Roadmap

## Working method

Codex owns requirements, task sequencing, review and release gates. Cursor owns bounded implementation. Each task is authored under `docs/tasks/`, then Cursor is launched in managed mode. Codex inspects its final report, diff, tests and deployment evidence; incomplete work receives a corrective task.

## Order

1. **PLAT-01** Create remote repository and local clean scaffold; copy approved docs; establish CI parity; no production cutover.
2. **WEB-01** Home page shell from the approved Home UX document.
3. **ID-01/02** Entra authentication, profile bootstrap, RBAC, audit and protected shell.
4. **DATA-01/02** Plaid private read-only integration.
5. **SIM-01–04** Multiple portfolios, wallet/ledger, quote policy, deterministic order/receipt and reconciliation.
6. **MRKT-01/02** Market ingestion and original research jobs rebuilt under the new platform.
7. **FORK-01/02** Portfolio versions, permissions, publishing and independent forks.
8. **AGENT-01–03** Agent registry/facts packets, research/forecast proposals, evaluations/cost/kill switch, later BYOM.
9. **COMM-01–03** Public profiles, discovery, follows, discussion/reports/moderation, reputation.
10. **MKT-01–03** Creator entitlements and marketplace, feature-flagged behind release gates.
11. **OPS-01–03** Full Azure job deployment, observability, controlled production cutover and rollback rehearsal.

No task may introduce a later-stage capability early. Background jobs are rebuilt in the market/research/agent phases, then deployed with the operations phase.
