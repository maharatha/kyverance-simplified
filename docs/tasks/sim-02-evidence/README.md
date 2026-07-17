# SIM-02 verification evidence

Branch: `codex/sim-02-order-loop`

## Scope confirmation

Implemented deterministic simulated market-order preview → explicit confirmation → immutable receipt/activity over SIM-01 ledger. Fixture quote mode only. No broker, Plaid, payments, agents, public forks, infrastructure, or original Kyverance changes.

## Commands and results

### Backend tests

```text
.\.venv\Scripts\python.exe -m pytest tests -q --tb=line
```

Result: **32 passed, 2 skipped**

### Migrations (local Postgres)

```text
.\.venv\Scripts\python.exe -m kyverance.db.migrate_cli upgrade head
```

Result: `0004_portfolios_ledger -> 0005_simulated_orders`

### Frontend

```text
npm test          → 13 files / 44 tests passed
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
