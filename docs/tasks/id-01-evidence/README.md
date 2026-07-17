# ID-01 verification evidence

Branch: `codex/id-01-entra-rbac`

## Commands and results

### Backend tests

```text
uv pip install -e ".[dev]" --python .venv\Scripts\python.exe
.\.venv\Scripts\python.exe -m pytest tests -q --tb=short
```

Result: **10 passed, 2 skipped**

### Frontend lint / tests / build

```text
npm run lint   → No ESLint warnings or errors
npm test       → 6 files / 24 tests passed
npm run build:clean → compiled successfully (Auth.js Edge Runtime jose warnings only)
```

### Migrations (local Postgres)

```text
.\.venv\Scripts\python.exe -m kyverance.db.migrate_cli upgrade head
.\.venv\Scripts\python.exe -m kyverance.db.migrate_cli downgrade 0001_foundation
.\.venv\Scripts\python.exe -m kyverance.db.migrate_cli upgrade head
.\.venv\Scripts\python.exe -m kyverance.db.migrate_cli current
```

Result: `0002_identity_rbac (head)` after upgrade/downgrade/upgrade cycle.

### API smoke

- `GET /health` → `{"status":"ok",...}`
- `GET /api/v1/me` with `APP_ENV=local` + `DEV_AUTH=true` → **200** bootstrap Member (`dev-user-001`)
- `GET /api/v1/me` with `APP_ENV=production` + `DEV_AUTH=false` + `X-Dev-Auth: true` → **401** (client header cannot enable development identity)
- Invalid Bearer → **401**

Artifacts: `api-dev-auth-smoke.txt`, `api-deny-smoke.txt`

### Web smoke

- Production start: `/` and `/sign-in` → **200**
- Screenshots:
  - `home-signed-out.png` — Home header shows **Sign in**
  - `sign-in.png` — Entra not configured message (production start)
  - `sign-in-local-dev.png` — **Continue as local developer** when `AUTH_DEV_IDENTITY=true` in development
- HTML captures: `home-signed-out.html`, `sign-in.html`, `sign-in-dev.html`

## Local non-secret fixtures

| Identity | Value |
| --- | --- |
| Development subject | `dev-user-001` |
| Display name | `Dev User` |
| Email (local only) | `dev@kyverance.local` |
| Default role | `member` |

No live Entra tenant IDs or client secrets were used.
