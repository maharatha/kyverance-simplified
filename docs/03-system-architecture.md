# System Architecture

## Decision

Use a modular monolith: Next.js 15/React 19/TypeScript web app; FastAPI/Pydantic/SQLAlchemy/Python 3.12 API; PostgreSQL/Alembic for durable state; Redis for cache/job coordination; Azure Blob for immutable research artifacts. Retain Azure Container Apps for API and jobs, ACR for images, Static Web Apps for web hosting, Key Vault for secrets, and Entra External ID for customer identity.

## Module boundaries

| Module | Owns | Must not do |
| --- | --- | --- |
| identity | Entra subject mapping, profile, roles, consents | return private objects by inference |
| portfolios | portfolios, versions, permissions, forks, snapshots | calculate social reputation |
| simulation | wallet ledger, order previews, executions, lots, receipts | route a real order |
| market_data | normalized quotes, freshness, EOD ingestion | expose provider tokens to web |
| research | canonical evidence/research artifacts and versioning | alter portfolio records |
| agents | agent registry, facts packets, proposals, forecasts, evaluations | bypass policy or confirm orders |
| community | profiles, follows, comments, reports, moderation | mutate performance history |
| marketplace | offerings, entitlements, payments/reconciliation | rank content or mirror trades |
| audit | immutable security/business audit events | become a transactional source of truth |

## Data/event rules

All money, quantity, price and performance values are database decimals and API decimal strings. Financial and entitlement mutations are transactional and idempotent. Ledger/executions, portfolio versions, published snapshots, grants, and audit events are append-only. Each meaningful transactional change writes an outbox event in the same transaction; workers are idempotent consumers. Derived projections may be rebuilt.

## Request flow

```text
Browser → Entra/Auth.js → FastAPI policy check → module service → PostgreSQL transaction + outbox
                                                           → Redis cache (read optimisation only)
Outbox/schedulers → Container Apps Jobs → market/research/agent/reconciliation work → Postgres/Blob
```

No model receives database credentials, raw Plaid tokens, a payment secret, a broad SQL tool, or an order-confirmation tool. The model only receives a minimal, authorized facts packet.

## Repository shape

```text
frontend/                 Next.js application
backend/src/kyverance/    FastAPI modules
backend/tests/            API/domain/integration tests
infrastructure/           local stack, Entra and Azure transition assets
.github/workflows/        CI and controlled deployment
docs/                     this source of truth and tasks
scripts/                  local/dev/operational commands
shared/                   intentionally small cross-language contracts
```
