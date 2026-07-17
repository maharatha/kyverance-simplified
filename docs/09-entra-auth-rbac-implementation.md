# ID-01 — Entra Authentication, RBAC, and Protected Application Shell

> Status: Implemented (pending Entra app-registration provisioning).  
> Parent: [Identity, permissions, and Plaid](04-identity-rbac-and-plaid.md).

## Outcome

Replace Home-page fixture identity with a secure Entra-aware application shell. A visitor can start sign-in; an authenticated user has a durable local profile and least-privilege role grants; protected web/API routes enforce identity and object-policy-ready authorization boundaries. The system must still run locally without cloud credentials using an explicit development-only identity mode.

## Technical decision

Reuse the original Kyverance pattern: Auth.js v5 with the Microsoft Entra ID provider, Entra External ID/CIAM authorization-code flow, server-side API JWT validation, Key Vault/environment-backed secrets, and branded hosted sign-in. Do not create or alter a live Entra registration in this task. The implementation consumes documented environment variables and verifies its configuration at startup.

## Scope

- Auth.js web configuration: session callbacks, sign-in/out, `/sign-in` UX, route middleware and a server session helper.
- Backend JWT verifier: issuer/audience/JWKS validation, a development-only explicit bypass, and normalized authenticated subject context.
- `users`, `role_grants`, and `consent_records` schema/migration plus bootstrap-on-first-sign-in service.
- Roles: Member, Creator, Moderator, Support, Finance Operations, Administrator, Agent Service. Member is the only default grant; role management is not exposed to end users.
- Authorization primitives: `require_authenticated`, `require_role`, actor/audit context, deny-by-default error semantics, and a protected `GET /api/v1/me` contract.
- Web/API tests for unauthenticated, development identity, default role, denied role, invalid JWT, and audit event behavior.

## Hard boundaries

- No Entra tenant/app-registration changes, live secret values, Key Vault writes, Azure deployment, Plaid, payments, creator entitlements, portfolio mutation, or database deletion.
- Development identity mode is disabled by default outside local development and never enabled by a client-controlled header in a deployed environment.
- Roles do not grant cross-user portfolio access. Object-level portfolio policy arrives with the portfolio domain.
- Never log tokens, authorization headers, client secrets, raw Entra claims, or personal email addresses.

## Acceptance criteria

- A missing/invalid token returns a neutral 401; a valid authenticated actor without a required role returns 403.
- A development identity can only be active behind a server-owned local feature setting.
- First sign-in creates/returns exactly one user and Member grant, without duplicate records under retries.
- Every role/consent mutation emits an append-only audit event with actor, target, action, safe metadata and timestamp.
- Home header renders a real session state interface rather than a fixture-only sign-in button when configuration is present.
- Backend tests, frontend lint/tests, and production build pass.
