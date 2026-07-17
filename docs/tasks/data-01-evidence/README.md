# DATA-01 verification evidence

Branch: `codex/data-01-plaid-readonly`

## DATA-01A Plaid runtime hardening

### Diagnosis

Acceptance checked `GET /` and `GET /settings/connected-accounts` with no Plaid credentials. The Connected Accounts page lived only at `/settings/connected`, so a signed-in probe of `/settings/connected-accounts` returned **404**. Concurrent Next.js `.next` cache corruption during DATA-01 also produced intermittent Home/settings **500**s (RSC/webpack manifest errors), which were mistaken for a Plaid-config failure.

### Fix summary

- Canonical route: `/settings/connected-accounts` (legacy `/settings/connected` redirects)
- Outside local/test, unset Plaid uses an unavailable provider (`configured=false`, `empty_state=configuration_required`, HTTP 200)
- Overview survives missing connector tables (HTTP 200 + configuration message) instead of SQL 500
- UI shows a clear unavailable/configuration state when Plaid is unset

### Commands and results

```text
backend pytest     → 19 passed, 2 skipped
npm test           → 9 files / 36 tests passed
npm run lint       → No ESLint warnings or errors
npm run build:clean → compiled successfully; `/settings/connected-accounts` included; Middleware 34.1 kB
```

### Unsigned / no-Plaid smoke

Artifact: `data-01a-runtime-smoke.txt`

- `GET /` → **200**
- `GET /api/auth/session` → **200** `null`
- `GET /settings/connected-accounts` (no cookie) → **307** → `/sign-in?callbackUrl=%2Fsettings%2Fconnected-accounts`
- `GET /settings/connected-accounts` (follow redirects) → **200**
- `GET /api/v1/connectors` (local, no Plaid) → **200**, `plaid_configured=false`, configuration message present

## Commands and results (DATA-01)

### Backend tests

```text
.\.venv\Scripts\python.exe -m pytest tests -q --tb=short
```

Result: **17 passed, 2 skipped** (pre-DATA-01A); **19 passed, 2 skipped** after DATA-01A

### Frontend lint / tests / build

```text
npm run lint        → No ESLint warnings or errors
npm test            → 9 files / 36 tests passed (after DATA-01A)
npm run build:clean → compiled successfully; `/settings/connected-accounts` included; Middleware 34.1 kB
```

### Migrations (local Postgres)

```text
.\.venv\Scripts\python.exe -m kyverance.db.migrate_cli upgrade head
.\.venv\Scripts\python.exe -m kyverance.db.migrate_cli downgrade 0002_identity_rbac
.\.venv\Scripts\python.exe -m kyverance.db.migrate_cli upgrade head
.\.venv\Scripts\python.exe -m kyverance.db.migrate_cli current
```

Result: `0003_plaid_readonly (head)` after upgrade/downgrade/upgrade cycle.

### Fake-provider API smoke

Artifact: `fake-provider-smoke.txt`

With `APP_ENV=local` + `DEV_AUTH=true` and no Plaid credentials:

| Step | Result |
|---|---|
| `GET /health` | 200 |
| `GET /api/v1/connectors` | 200, `mode=fake`, `empty_state=consent_required` |
| `POST /api/v1/connectors/plaid/consent` | 200, consent granted |
| `POST /api/v1/connectors/plaid/fake-connect` | 200, sample accounts/holdings with `plaid_read_only` provenance |
| `POST .../refresh` | 200 |
| Secret leak check | `SECRET_LEAK=false` (no access token / ciphertext in JSON) |
| `DELETE .../connections/{id}` | 200, status `disconnected` |

## Scope confirmation

- No Plaid / Azure / Entra / Key Vault / GitHub secrets / DNS / deployment changes
- No original Kyverance modifications
- No live banking connections, orders, funding, public sharing, or simulation links
