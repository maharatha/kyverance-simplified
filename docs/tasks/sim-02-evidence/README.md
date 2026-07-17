# SIM-02 verification evidence

Branch: `codex/sim-02-order-loop`

## SIM-02A order runtime hardening

### Diagnosis

Acceptance probed `http://127.0.0.1:3001` (Home then `/portfolios`) during concurrent SIM-02 `next dev` / build activity. The shared `.next` cache was corrupted (RSC Client Manifest / webpack pack ENOENT), producing intermittent **500**s unrelated to fixture quotes. SIM-02 also coupled portfolio detail load to positions/activity via `Promise.all`, so a stale API without order routes or unmigrated SIM-02 tables blanked the workspace.

### Fix summary

- Portfolio detail soft-fails positions/activity and still renders wallet/ledger + order panel
- Positions/activity APIs return empty HTTP 200 lists when order tables are missing
- Non-fixture `QUOTE_MODE` remains fail-closed (`503`)

### Commands and results (SIM-02A)

```text
backend pytest     → 34 passed, 2 skipped
npm test           → 14 files / 45 tests passed
npm run lint       → No ESLint warnings or errors
npm run build:clean → compiled successfully; /portfolios/[id] 3.51 kB
```

### Runtime smoke

Artifact: `sim-02a-runtime-smoke.txt`

- `GET /` → **200**
- `GET /portfolios` → **200**
- `GET /portfolios/{id}` → **200**
- Fixture preview → **200**, `data_mode=fixture`

## Scope confirmation

Implemented deterministic simulated market-order preview → explicit confirmation → immutable receipt/activity over SIM-01 ledger. Fixture quote mode only. No broker, Plaid, payments, agents, public forks, infrastructure, or original Kyverance changes.

## Commands and results

### Backend tests

```text
.\.venv\Scripts\python.exe -m pytest tests -q --tb=line
```

Result: **32 passed, 2 skipped** (SIM-02); **34 passed, 2 skipped** after SIM-02A

### Migrations (local Postgres)

```text
.\.venv\Scripts\python.exe -m kyverance.db.migrate_cli upgrade head
```

Result: `0004_portfolios_ledger -> 0005_simulated_orders`

### Frontend

```text
npm test          → 13 files / 44 tests passed (SIM-02); 14 files / 45 after SIM-02A
npm run lint      → No ESLint warnings or errors
npm run build:clean → compiled successfully; /portfolios/[id] 3.5 kB
```

## Behavior covered

- Preview returns decimal strings, fixture data mode, freshness + execution policy labels
- Confirm requires `Idempotency-Key` and binds to `preview_id`
- Same key replays receipt; different preview conflicts (409)
- Insufficient cash / oversell leave no partial writes
- Object authorization returns 404 for foreign portfolios
- Sell round-trip clears position; reconciliation `ok`
- UI requires separate Confirm after Preview
- Portfolio workspace survives missing order tables / soft-fails positions+activity (SIM-02A)
