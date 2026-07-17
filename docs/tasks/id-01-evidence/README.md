# ID-01 verification evidence

Branch: `codex/id-01-entra-rbac`

## ID-01A Auth.js runtime hardening

### Diagnosis

With no `.env.local` / Entra credentials, Edge middleware imported `next-auth` and Auth.js threw `MissingSecret`. `GET /api/auth/session` returned **500**, breaking the signed-out shell.

### Fix summary

- Edge middleware: cookie presence gate only (`lib/auth-routes.ts`) — no Auth.js/Jose import
- Node `auth.ts`: providers + jwt/session callbacks + `resolveAuthSecret()`
- Non-production local secret fallback; production remains fail-closed without `AUTH_SECRET`

### Commands and results

```text
npm test          → 7 files / 31 tests passed
npm run lint      → No ESLint warnings or errors
npm run build:clean → compiled successfully; Middleware 34.1 kB; no Edge jose warning
backend pytest    → 10 passed, 2 skipped
```

### Unsigned smoke (no AUTH_SECRET / Entra / AUTH_DEV_IDENTITY)

Artifact: `id-01a-runtime-smoke.txt`

- `GET /` → **200**
- `GET /sign-in` → **200**
- `GET /api/auth/session` → **200** `null`
- `GET /profile` → **307** `/sign-in?callbackUrl=%2Fprofile`

HTML: `id-01a-home-unsigned.html`, `id-01a-sign-in-unsigned.html`

## Commands and results (ID-01)

### Backend tests

```text
uv pip install -e ".[dev]" --python .venv\Scripts\python.exe
.\.venv\Scripts\python.exe -m pytest tests -q --tb=short
```

Result: **10 passed, 2 skipped**

### Frontend lint / tests / build

```text
npm run lint   → No ESLint warnings or errors
npm test       → 7 files / 31 tests passed (after ID-01A)
npm run build:clean → compiled successfully; Middleware 34.1 kB (no Edge jose warning after ID-01A)
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
