# Simulation, Forks, Community, and Marketplace

## Simulation

Each user may own many simulated portfolios. Each portfolio has a simulation wallet, ledger, positions/lots, theses, order previews, orders, executions, receipts and derived valuations. The only financial mutation path is: user intent → server preview → explicit confirmation with idempotency key → one transaction creating source records → receipt. A model may draft an intent but cannot cross confirmation.

Market-only US equity/ETF simulation is the first supported execution policy. Quotes carry provider/as-of/received/freshness metadata. The UI labels data mode and simulated status at the decision and receipt. Reconciliation recomputes cash from ledger and quantities from executions; any discrepancy blocks affected mutations and opens an audit incident.

## Version and fork model

A portfolio version freezes portfolio metadata, thesis/rules, holdings/allocation, data context, optional approved agent configuration, and a checksum. Publishing requires explicit consent, visibility choice, provenance and disclosure. A fork creates a new owner-controlled simulated portfolio from exactly one source version. It stores source portfolio/version, fork license/entitlement, timestamp and divergence history. It does not receive source updates, trade mirrors, payment permission, or the source owner’s private data.

## Community

Public portfolios show provenance, as-of time, history length, risk/data sufficiency and simulation status before performance. Discovery defaults to process/research/risk filters—not raw return. Follow, structured comments, reports, moderation and explainable process reputation are available only after the underlying policy and anti-abuse tests. No public leaderboard ships before its governance model and legal review are approved.

## Creator marketplace

An offering can grant paid access to defined content: research artifacts, private version history, template/fork rights, or an approved private discussion. An entitlement does not grant ownership of a source portfolio, access to Plaid data, real-trade authority, or automatic synchronization. Stripe/payment work remains behind a dedicated privacy, tax, jurisdiction, refund, disclosure, moderation, security and reconciliation gate.
