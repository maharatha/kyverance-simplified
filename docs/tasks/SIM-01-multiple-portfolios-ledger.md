# SIM-01 — Multiple simulated portfolios and canonical ledger

> Status: Implemented on `codex/sim-01-portfolios-ledger`

Implement the first simulation domain slice: authenticated users can own multiple private simulated portfolios, each with an isolated virtual wallet and immutable ledger. Add database migrations, decimal-string API contracts, object authorization, creation/list/read endpoints, and a minimal portfolio workspace UI. Reuse original Kyverance simulation principles: no floating point, no cross-portfolio cash, source records before projections, audit events, and idempotent creation. Do not implement market orders, Plaid linkage, public publishing/forks, payments, live brokerage, Azure changes, or real market data. Run backend/frontend tests and production build; commit/push on `codex/sim-01-portfolios-ledger`.
