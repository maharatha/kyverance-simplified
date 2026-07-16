# Identity, Permissions, and Plaid

## Entra

Preserve the original pattern: Microsoft Entra External ID customer tenant, `SignUpSignIn` user flow, Auth.js v5 web integration, OIDC authorization-code flow, API JWT audience validation, Key Vault-held credentials, and the original branded sign-in assets as a starting point. The new repository receives distinct app registration credentials and redirect URIs before production cutover; it must not silently reuse an old redirect configuration.

## RBAC and object policy

Global roles are Member, Creator, Moderator, Support, Finance Operations, Administrator, and Agent Service. Roles are additive but least-privilege. Every request also requires object-level authorization: ownership, a granted collaboration role, a valid creator entitlement, visibility plus consent, or a documented moderator/support policy. Record role changes, privileged reads, consent changes, publication, payment actions, agent grants, and admin actions in the audit log.

## Plaid

Plaid is read-only and private by default. Connection tokens and access tokens are server-only, encrypted/Key-Vault-backed, never sent to the browser, never logged, and revocable. Imported account/holding data is a distinct provenance from simulation and cannot fund virtual cash, become a public portfolio, or appear in marketplace content without a later explicit consent/policy release. The product supports connection, explicit consent, refresh status, disconnect, deletion request, and a plain-language source label.

## First implementation sequence

1. Entra/Auth.js app shell and signed-in subject bootstrap.
2. Database role/consent model plus API policy helpers and audit events.
3. Role-safe Home state and protected routes.
4. Plaid Link exchange/server token vaulting and read-only data ingestion.
5. Account/holding display with source, consent, refresh, disconnect and deletion controls.
