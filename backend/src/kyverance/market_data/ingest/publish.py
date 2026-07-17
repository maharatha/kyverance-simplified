"""Transactional publication of validated EOD batches + latest snapshot."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from kyverance.config import get_settings
from kyverance.market_data.constants import DATA_STATUS_FINAL, INGEST_STATUS_PUBLISHED
from kyverance.market_data.dto import NormalizedDailyPrice, ValidationIssue
from kyverance.market_data.models import DailyPrice, IngestionError, IngestionRun, LatestDailyPrice


def record_errors(db: Session, run_id: UUID, issues: list[ValidationIssue]) -> None:
    settings = get_settings()
    max_unmapped = max(0, int(settings.market_data_max_unmapped_errors or 0))
    unmapped = [i for i in issues if i.error_type == "unmapped_instrument"]
    other = [i for i in issues if i.error_type != "unmapped_instrument"]
    to_persist = list(other)
    if max_unmapped > 0:
        to_persist.extend(unmapped[:max_unmapped])
        if len(unmapped) > max_unmapped:
            to_persist.append(
                ValidationIssue(
                    error_type="unmapped_instrument",
                    message=(
                        f"Truncated unmapped_instrument errors: showing {max_unmapped} of {len(unmapped)}"
                    ),
                    provider_record_identifier="summary",
                    severity="warning",
                )
            )
    else:
        to_persist.extend(unmapped)

    for issue in to_persist:
        if issue.severity != "error" and issue.error_type not in {
            "unmapped_instrument",
            "incomplete_batch",
        }:
            if issue.severity == "warning":
                continue
        db.add(
            IngestionError(
                id=uuid4(),
                ingestion_run_id=run_id,
                provider_record_identifier=issue.provider_record_identifier,
                error_type=issue.error_type,
                error_message=issue.message,
                raw_record_json=issue.raw_record,
            )
        )


def publish_daily_prices(
    db: Session,
    *,
    run: IngestionRun,
    rows: list[NormalizedDailyPrice],
    provider_id: UUID,
    bump_version: bool = False,
) -> dict[str, int]:
    """Upsert daily_prices + latest_daily_prices. Caller commits."""
    if not rows:
        run.records_inserted = run.records_inserted or 0
        run.records_updated = run.records_updated or 0
        run.status = INGEST_STATUS_PUBLISHED
        run.completed_at = datetime.now(timezone.utc)
        return {"inserted": 0, "updated": 0}

    inserted = 0
    updated = 0
    now = datetime.now(timezone.utc)
    trading_date = rows[0].trading_date
    listing_ids = [UUID(r.instrument_listing_id) for r in rows]

    existing_by_listing: dict[UUID, DailyPrice] = {
        row.instrument_listing_id: row
        for row in db.query(DailyPrice)
        .filter(DailyPrice.trading_date == trading_date, DailyPrice.instrument_listing_id.in_(listing_ids))
        .all()
    }
    latest_by_listing: dict[UUID, LatestDailyPrice] = {
        row.instrument_listing_id: row
        for row in db.query(LatestDailyPrice)
        .filter(LatestDailyPrice.instrument_listing_id.in_(listing_ids))
        .all()
    }

    for row in rows:
        listing_id = UUID(row.instrument_listing_id)
        existing = existing_by_listing.get(listing_id)
        if existing:
            changed = (
                existing.close != row.close
                or existing.open != row.open
                or existing.high != row.high
                or existing.low != row.low
                or existing.volume != row.volume
            )
            if not changed and not bump_version:
                version = int(existing.data_version or 1)
            else:
                next_version = int(existing.data_version or 1) + (1 if bump_version or changed else 0)
                existing.open = row.open
                existing.high = row.high
                existing.low = row.low
                existing.close = row.close
                existing.adjusted_close = row.adjusted_close
                existing.volume = row.volume
                existing.currency_code = row.currency_code
                existing.provider_id = provider_id
                existing.source_updated_at = row.source_updated_at
                existing.data_status = DATA_STATUS_FINAL
                existing.data_version = next_version
                existing.updated_at = now
                updated += 1
                version = next_version
        else:
            db.add(
                DailyPrice(
                    instrument_listing_id=listing_id,
                    trading_date=row.trading_date,
                    open=row.open,
                    high=row.high,
                    low=row.low,
                    close=row.close,
                    adjusted_close=row.adjusted_close,
                    volume=row.volume,
                    currency_code=row.currency_code,
                    provider_id=provider_id,
                    source_updated_at=row.source_updated_at,
                    data_status=DATA_STATUS_FINAL,
                    data_version=1,
                )
            )
            inserted += 1
            version = 1

        latest = latest_by_listing.get(listing_id)
        if latest is None or row.trading_date >= latest.trading_date:
            if latest is None:
                latest = LatestDailyPrice(instrument_listing_id=listing_id)
                db.add(latest)
                latest_by_listing[listing_id] = latest
            latest.trading_date = row.trading_date
            latest.open = row.open
            latest.high = row.high
            latest.low = row.low
            latest.close = row.close
            latest.adjusted_close = row.adjusted_close
            latest.volume = row.volume
            latest.currency_code = row.currency_code
            latest.provider_id = provider_id
            latest.data_status = DATA_STATUS_FINAL
            latest.data_version = version
            latest.updated_at = now

    run.records_inserted = (run.records_inserted or 0) + inserted
    run.records_updated = (run.records_updated or 0) + updated
    run.status = INGEST_STATUS_PUBLISHED
    run.completed_at = now
    return {"inserted": inserted, "updated": updated}
