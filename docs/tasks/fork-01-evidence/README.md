# FORK-01 verification evidence

Branch: `codex/fork-01-versioned-portfolios`

## Scope confirmation

Implemented immutable portfolio versions (metadata/thesis/holdings/agent-config ref/data context/checksum), publish with explicit consent/visibility/provenance/license, and independent forks with durable lineage + isolated wallet/positions. No automatic sync, mirrored trades, discovery feeds, marketplace/payments, Plaid exposure, real trading, or original Kyverance edits.

## Commands and results

### Backend tests

```text
.\.venv\Scripts\python.exe -m pytest tests -q --tb=line
```

Result: **39 passed, 2 skipped**

### Frontend

```text
npm test          → 14 files / 48 tests passed
npm run lint      → No ESLint warnings or errors
npm run build:clean → compiled successfully; /portfolios/[id] 4.98 kB
```

## Behavior covered

- Version snapshot freezes thesis/holdings/checksum; live portfolio edits do not mutate prior versions
- Publish requires creator role + explicit consent; published policy cannot be rewritten in place
- Fork from `public` + `public_fork_allowed` creates private portfolio with independent wallet/positions and lineage (`sync_enabled=false`, `mirror_trades=false`)
- Private/draft foreign versions return 404; view_only public versions deny fork (403)
- UI: thesis/version/publish panel on portfolio detail; fork-by-version-id on portfolios list

## Migration / rollout

Alembic revision `0006_portfolio_versions_forks`:

- Adds `portfolios.thesis`, `portfolios.agent_config_ref`
- Creates `portfolio_versions`, `portfolio_forks`
- Makes `sim_position_lots.execution_id` nullable for fork-seeded lots

Apply with: `python -m kyverance.db.migrate_cli upgrade head`

## Risks

- Creator role must be granted before publish (members can still create draft versions and fork)
- Fork seed lots have null `execution_id`; sells remain FIFO against those lots
- No discovery feed: fork UX requires a known public version ID
