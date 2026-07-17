"""Morning reconciliation checks for an exchange. Never mutates financial tables."""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from kyverance.market_data.constants import INGEST_STATUS_PUBLISHED, JOB_DAILY_EOD
from kyverance.market_data.models import (
    DailyPrice,
    IngestionRun,
    InstrumentListing,
    LatestDailyPrice,
    MarketExchange,
)

logger = logging.getLogger(__name__)


def run_reconcile(db: Session, *, exchange_canonical: str, trading_date: str) -> dict:
    exchange = (
        db.query(MarketExchange)
        .filter(MarketExchange.canonical_code == exchange_canonical.upper())
        .one()
    )
    d = date.fromisoformat(trading_date)
    alerts: list[str] = []

    run = (
        db.query(IngestionRun)
        .filter(
            IngestionRun.exchange_id == exchange.id,
            IngestionRun.trading_date == d,
            IngestionRun.job_type == JOB_DAILY_EOD,
        )
        .one_or_none()
    )
    if run is None or run.status != INGEST_STATUS_PUBLISHED:
        alerts.append("missing_or_unpublished_daily_eod")

    listing_ids = [
        r.id
        for r in db.query(InstrumentListing.id)
        .filter(InstrumentListing.exchange_id == exchange.id, InstrumentListing.is_active.is_(True))
        .all()
    ]
    if listing_ids:
        price_count = (
            db.query(func.count())
            .select_from(DailyPrice)
            .filter(DailyPrice.trading_date == d, DailyPrice.instrument_listing_id.in_(listing_ids))
            .scalar()
            or 0
        )
        if price_count == 0:
            alerts.append("zero_prices_for_date")

        current = (
            db.query(func.count())
            .select_from(LatestDailyPrice)
            .filter(
                LatestDailyPrice.instrument_listing_id.in_(listing_ids),
                LatestDailyPrice.trading_date == d,
            )
            .scalar()
            or 0
        )
        if current == 0 and price_count > 0:
            alerts.append("latest_snapshot_not_aligned")

    status = "ok" if not alerts else "alert"
    logger.info(
        "market_data.reconcile exchange=%s trading_date=%s status=%s alerts=%s",
        exchange_canonical,
        trading_date,
        status,
        alerts,
    )
    return {
        "exchange": exchange_canonical,
        "trading_date": trading_date,
        "status": status,
        "alerts": alerts,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }
