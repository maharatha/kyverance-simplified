"""Daily EOD ingestion for one exchange + trading date."""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from kyverance.config import get_settings
from kyverance.market_data.constants import (
    INGEST_STATUS_DOWNLOADED,
    INGEST_STATUS_FAILED,
    INGEST_STATUS_NORMALIZED,
    INGEST_STATUS_PARTIALLY_FAILED,
    INGEST_STATUS_QUEUED,
    INGEST_STATUS_RUNNING,
    INGEST_STATUS_VALIDATED,
    JOB_DAILY_EOD,
)
from kyverance.market_data.ingest.normalize import build_symbol_map, normalize_prices
from kyverance.market_data.ingest.publish import publish_daily_prices, record_errors
from kyverance.market_data.ingest.validate import validate_batch
from kyverance.market_data.models import DataProvider, IngestionRun, MarketDataHealth, MarketExchange
from kyverance.market_data.providers.registry import get_market_data_provider

logger = logging.getLogger(__name__)


def _touch_health(db: Session, *, success: bool, message: str) -> None:
    row = db.get(MarketDataHealth, "ingest")
    now = datetime.now(timezone.utc)
    if row is None:
        row = MarketDataHealth(component="ingest")
        db.add(row)
    if success:
        row.last_success_at = now
    else:
        row.last_error_at = now
    row.last_message = message[:2000]
    row.updated_at = now


async def run_daily_eod(
    db: Session,
    *,
    exchange_canonical: str,
    trading_date: str,
    job_type: str = JOB_DAILY_EOD,
    bump_version: bool = False,
) -> dict:
    settings = get_settings()
    provider = get_market_data_provider(settings)
    dp = db.query(DataProvider).filter(DataProvider.code == provider.code).one()
    exchange = (
        db.query(MarketExchange)
        .filter(MarketExchange.canonical_code == exchange_canonical.upper())
        .one()
    )
    d = date.fromisoformat(trading_date)

    run = (
        db.query(IngestionRun)
        .filter(
            IngestionRun.provider_id == dp.id,
            IngestionRun.exchange_id == exchange.id,
            IngestionRun.job_type == job_type,
            IngestionRun.trading_date == d,
        )
        .one_or_none()
    )
    if run is None:
        run = IngestionRun(
            id=uuid4(),
            provider_id=dp.id,
            exchange_id=exchange.id,
            job_type=job_type,
            trading_date=d,
            status=INGEST_STATUS_QUEUED,
        )
        db.add(run)
        db.flush()

    prior_status = (run.status or "").upper()
    if prior_status in {INGEST_STATUS_FAILED, INGEST_STATUS_PARTIALLY_FAILED}:
        run.retry_count = int(run.retry_count or 0) + 1
    run.status = INGEST_STATUS_RUNNING
    run.started_at = datetime.now(timezone.utc)
    run.error_code = None
    run.error_message = None
    db.commit()
    db.refresh(run)

    logger.info(
        "market_data.ingest.start run_id=%s provider=%s exchange=%s trading_date=%s job_type=%s",
        run.id,
        provider.code,
        exchange.canonical_code,
        trading_date,
        job_type,
    )

    try:
        # Provider bulk is exchange-agnostic for US fake/live contract ("US").
        prices = await provider.get_exchange_eod("US", trading_date)
        run.status = INGEST_STATUS_DOWNLOADED
        run.records_received = len(prices)
        db.commit()

        symbol_map = build_symbol_map(db, dp.id)
        normalized, map_issues = normalize_prices(prices, symbol_map=symbol_map)
        run.status = INGEST_STATUS_NORMALIZED
        run.records_normalized = len(normalized)
        db.commit()

        accepted, val_issues, publish_ok = validate_batch(
            normalized,
            expected_min_count=max(1, len(symbol_map) // 50) if symbol_map else None,
            settings=settings,
        )
        issues = map_issues + val_issues
        record_errors(db, run.id, issues)
        run.records_rejected = len([i for i in issues if i.severity == "error"])
        run.status = INGEST_STATUS_VALIDATED
        db.commit()

        if not publish_ok:
            run.status = INGEST_STATUS_PARTIALLY_FAILED if accepted else INGEST_STATUS_FAILED
            run.error_code = "validation_failed"
            run.error_message = "Batch failed validation/completeness"
            run.completed_at = datetime.now(timezone.utc)
            _touch_health(db, success=False, message=run.error_message)
            db.commit()
            return {"status": run.status, "run_id": str(run.id), "accepted": len(accepted)}

        stats = publish_daily_prices(
            db, run=run, rows=accepted, provider_id=dp.id, bump_version=bump_version
        )
        _touch_health(db, success=True, message=f"published {trading_date}")
        db.commit()
        return {
            "status": "PUBLISHED",
            "run_id": str(run.id),
            "received": len(prices),
            "accepted": len(accepted),
            **stats,
        }
    except Exception as exc:  # noqa: BLE001
        logger.exception("market_data.ingest.failed run_id=%s", run.id)
        run.status = INGEST_STATUS_FAILED
        run.error_code = type(exc).__name__
        run.error_message = str(exc)[:2000]
        run.completed_at = datetime.now(timezone.utc)
        _touch_health(db, success=False, message=str(exc))
        db.commit()
        raise
