# ADR 0001 — Modular monolith and runtime baseline

## Status

Accepted

## Context

Kyverance Simplified inherits the approved technology choices from the original Kyverance platform while rebuilding the application from a clean repository and schema.

## Decision

Use a modular monolith with:

- Next.js 15 / React 19 / TypeScript for the web app
- FastAPI / Pydantic / SQLAlchemy / Alembic / Python 3.12 for the API
- PostgreSQL for durable state and Redis for cache/job coordination
- Module packages under `backend/src/kyverance/` matching the boundaries in `docs/03-system-architecture.md`

Do not copy original application source, secrets, databases, or production configuration wholesale.

## Consequences

- CI mirrors the original guarantees: backend pytest with Postgres/Redis services, and a clean frontend production build.
- Domain features arrive in later tasks; this repository starts as a runnable shell.
- Azure, Entra, Plaid, and marketplace work remain out of scope until their dedicated tasks.
