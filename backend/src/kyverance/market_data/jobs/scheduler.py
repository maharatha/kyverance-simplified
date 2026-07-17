"""Exchange-aware market-data scheduler — enqueues only; never calls providers."""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from uuid import uuid4
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from kyverance.config import get_settings
from kyverance.db.session import SessionLocal
from kyverance.market_data.jobs import queue
from kyverance.market_data.jobs.types import (
    JOB_CORRECTION,
    JOB_DAILY_EOD,
    JOB_RECONCILE,
    JOB_SYNC_EXCHANGES,
    JOB_SYNC_INSTRUMENTS,
)
from kyverance.market_data.models import ExchangeTradingDay, MarketDataHealth, MarketExchange

logger = logging.getLogger(__name__)


def ensure_weekday_calendar(db: Session, exchange: MarketExchange, year: int) -> int:
    """Seed Mon–Fri trading days when exchange_calendars is unavailable."""
    start = date(year, 1, 1)
    end = date(year, 12, 31)
    existing = {
        r.trading_date
        for r in db.query(ExchangeTradingDay.trading_date)
        .filter(ExchangeTradingDay.exchange_id == exchange.id)
        .filter(ExchangeTradingDay.trading_date >= start, ExchangeTradingDay.trading_date <= end)
        .all()
    }
    created = 0
    d = start
    while d <= end:
        if d.weekday() < 5 and d not in existing:
            db.add(
                ExchangeTradingDay(
                    id=uuid4(),
                    exchange_id=exchange.id,
                    trading_date=d,
                    is_trading_day=True,
                    open_time=exchange.regular_open_time,
                    close_time=exchange.regular_close_time,
                    source="weekday_seed",
                )
            )
            created += 1
        d += timedelta(days=1)
    if created:
        db.commit()
    return created


def _session_ready(
    exchange: MarketExchange, session_day: date, now_utc: datetime, delay_minutes: int
) -> bool:
    tz = ZoneInfo(exchange.timezone or "America/New_York")
    close_h, close_m = (exchange.regular_close_time or "16:00").split(":")
    close_local = datetime(
        session_day.year,
        session_day.month,
        session_day.day,
        int(close_h),
        int(close_m),
        tzinfo=tz,
    )
    ready_at = close_local.astimezone(timezone.utc) + timedelta(minutes=delay_minutes)
    return now_utc >= ready_at


def schedule_once(db: Session | None = None, *, now: datetime | None = None) -> dict:
    settings = get_settings()
    if not settings.market_data_jobs_enabled:
        return {"enqueued": [], "skipped": "market_data_jobs_disabled"}

    own_session = db is None
    session = db or SessionLocal()
    try:
        now_utc = now or datetime.now(timezone.utc)
        enqueued: list[str] = []
        exchanges = session.query(MarketExchange).filter(MarketExchange.is_active.is_(True)).all()
        primary_us = (settings.market_data_us_primary_exchange or "XNAS").upper()
        us_bulk_enqueued = False

        for ex in exchanges:
            ensure_weekday_calendar(session, ex, now_utc.year)
            tz = ZoneInfo(ex.timezone or "America/New_York")
            local_today = now_utc.astimezone(tz).date()
            day_row = (
                session.query(ExchangeTradingDay)
                .filter(
                    ExchangeTradingDay.exchange_id == ex.id,
                    ExchangeTradingDay.is_trading_day.is_(True),
                    ExchangeTradingDay.trading_date <= local_today,
                )
                .order_by(ExchangeTradingDay.trading_date.desc())
                .first()
            )
            if not day_row:
                continue
            session_day = day_row.trading_date
            delay = (
                ex.default_data_availability_delay_minutes
                or settings.market_data_default_availability_delay_minutes
            )
            if not _session_ready(ex, session_day, now_utc, delay):
                continue

            is_us = (ex.country_code or "").upper() == "US" or ex.canonical_code.upper() in {
                "XNAS",
                "XNYS",
            }
            if is_us:
                if us_bulk_enqueued or ex.canonical_code.upper() != primary_us:
                    prior = (
                        session.query(ExchangeTradingDay)
                        .filter(
                            ExchangeTradingDay.exchange_id == ex.id,
                            ExchangeTradingDay.is_trading_day.is_(True),
                            ExchangeTradingDay.trading_date < session_day,
                        )
                        .order_by(ExchangeTradingDay.trading_date.desc())
                        .first()
                    )
                    if prior and now_utc.astimezone(tz).hour >= 8:
                        rkey = f"reconcile:{ex.canonical_code}:{prior.trading_date.isoformat()}"
                        queue.enqueue_job(
                            session,
                            job_type=JOB_RECONCILE,
                            idempotency_key=rkey,
                            payload={
                                "exchange": ex.canonical_code,
                                "trading_date": prior.trading_date.isoformat(),
                            },
                        )
                        enqueued.append(rkey)
                    continue
                us_bulk_enqueued = True

            key = f"daily-eod:{ex.canonical_code}:{session_day.isoformat()}"
            queue.enqueue_job(
                session,
                job_type=JOB_DAILY_EOD,
                idempotency_key=key,
                payload={"exchange": ex.canonical_code, "trading_date": session_day.isoformat()},
            )
            enqueued.append(key)

            corr_delay = settings.market_data_correction_delay_minutes
            if _session_ready(ex, session_day, now_utc, delay + corr_delay):
                ckey = f"correction:{ex.canonical_code}:{session_day.isoformat()}"
                queue.enqueue_job(
                    session,
                    job_type=JOB_CORRECTION,
                    idempotency_key=ckey,
                    payload={
                        "exchange": ex.canonical_code,
                        "trading_date": session_day.isoformat(),
                    },
                )
                enqueued.append(ckey)

            prior = (
                session.query(ExchangeTradingDay)
                .filter(
                    ExchangeTradingDay.exchange_id == ex.id,
                    ExchangeTradingDay.is_trading_day.is_(True),
                    ExchangeTradingDay.trading_date < session_day,
                )
                .order_by(ExchangeTradingDay.trading_date.desc())
                .first()
            )
            if prior and now_utc.astimezone(tz).hour >= 8:
                rkey = f"reconcile:{ex.canonical_code}:{prior.trading_date.isoformat()}"
                queue.enqueue_job(
                    session,
                    job_type=JOB_RECONCILE,
                    idempotency_key=rkey,
                    payload={
                        "exchange": ex.canonical_code,
                        "trading_date": prior.trading_date.isoformat(),
                    },
                )
                enqueued.append(rkey)

        week = now_utc.strftime("%G-W%V")
        queue.enqueue_job(
            session,
            job_type=JOB_SYNC_EXCHANGES,
            idempotency_key=f"sync-exchanges:{week}",
            payload={},
        )
        sync_limit = int(settings.market_data_instrument_sync_limit or 0)
        sync_payload: dict = {"exchange": primary_us}
        if sync_limit > 0:
            sync_payload["limit"] = sync_limit
        queue.enqueue_job(
            session,
            job_type=JOB_SYNC_INSTRUMENTS,
            idempotency_key=f"sync-instruments:{primary_us}:{now_utc.date().isoformat()}",
            payload=sync_payload,
        )
        enqueued.append(f"sync-exchanges:{week}")
        enqueued.append(f"sync-instruments:{primary_us}:{now_utc.date().isoformat()}")

        health = session.get(MarketDataHealth, "scheduler")
        if health is None:
            health = MarketDataHealth(component="scheduler")
            session.add(health)
        health.last_success_at = now_utc
        health.last_message = f"enqueued={len(enqueued)}"
        health.updated_at = now_utc
        session.commit()

        return {"enqueued": enqueued, "at": now_utc.isoformat()}
    finally:
        if own_session:
            session.close()


def main(argv: list[str] | None = None) -> None:
    _ = argv
    logging.basicConfig(level=logging.INFO)
    result = schedule_once()
    logger.info("market_data.scheduler.result %s", result)


if __name__ == "__main__":
    main()
