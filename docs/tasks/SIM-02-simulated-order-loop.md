# SIM-02 — Deterministic simulated order loop

> Status: Implemented on `codex/sim-02-order-loop`

Implement simulated market-order preview, explicit confirmation, immutable receipt/activity, and reconciliation over SIM-01’s ledger. Use server-side decimal arithmetic, quote freshness/policy labels, object authorization and Idempotency-Key replay. A user must confirm after preview; no agent, Plaid, broker, payment, public fork, or automated execution may place an order. Add unit/API/frontend tests, safe fixture quote mode, and evidence; commit/push on a focused branch only after checks pass.
