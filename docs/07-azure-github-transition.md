# Azure and GitHub Transition

## Objective

Move delivery from the original `kyverance` repository to a new `kyverance-simplified` repository while retaining the established Azure topology, security model, CI checks, and ability to roll back. The original application remains deployable until the new application passes production gates.

## Preserve

- GitHub Actions CI: Python tests with PostgreSQL/Redis services; clean Next.js production build.
- GitHub Actions OIDC Azure login; ACR image deployment to Container Apps; SWA deployment; Key Vault secret references.
- Entra External ID identity model; Container Apps/Jobs operational pattern; Postgres/Redis/Blob/observability runbooks.

## Transition rules

1. Create new repository, CI workflows and a separate development deployment identity/configuration first.
2. Export no secrets into the repository. Recreate GitHub environment secrets and Azure role assignments through approved secure configuration.
3. Initially deploy the new API/web under separate application names and non-production hostnames, pointed at a clean new database. Existing production resources continue serving the original application.
4. Rebuild database schema from zero in the new database. Destructive recreation is authorized only for this new simplified database—not for the original Kyverance production database.
5. Migrate/recreate background jobs against the new image and database; verify each job independently.
6. Cut over production DNS/host bindings only after CI, smoke tests, Entra redirects, migrations, backups, observability, job readiness, security review, and rollback route are verified.
7. Rollback is traffic/DNS/host-binding return to the original application, not a destructive reversal of either database.

## Deployment authority and safety

The user authorizes creation/deployment for this new product and clean new database. We still do not delete or overwrite the original Kyverance database, secrets, host bindings, or production application until an explicit automated cutover task meets its documented gates. Legal, tax, payment, market-data licensing, privacy and public-community release gates cannot be self-certified by an agent; features dependent on them remain feature-flagged until documented external approval exists.

## Required CI/CD stages

`lint/test/build` → preview/dev deploy → API/web/job smoke checks → migration/reconciliation checks → staged production deployment → post-deploy health/telemetry check. Every deploy identifies image SHA, migration version, configuration version and rollback target.
