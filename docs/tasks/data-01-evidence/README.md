# DATA-01 verification evidence

Branch: `codex/data-01-plaid-readonly`

## Commands and results

### Backend tests

```text
.\.venv\Scripts\python.exe -m pytest tests -q --tb=short
```

Result: **17 passed, 2 skipped**

### Frontend lint / tests / build

```text
npm run lint        → No ESLint warnings or errors
npm test            → 9 files / 35 tests passed
npm run build:clean → compiled successfully; `/settings/connected` included; Middleware 34.1 kB
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
