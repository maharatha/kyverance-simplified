"""Exchange-aware calendar helpers for research scheduling."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from kyverance.market_data.models import ExchangeTradingDay, MarketExchange

_NY = ZoneInfo("America/New_York")


def us_market_date(as_of: datetime | None = None) -> date:
    now = as_of or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    return now.astimezone(_NY).date()


def is_trading_day(db: Session | None, d: date, *, exchange_code: str = "XNAS") -> bool:
    if db is not None:
        exchange = (
            db.query(MarketExchange)
            .filter(MarketExchange.canonical_code == exchange_code.upper())
            .one_or_none()
        )
        if exchange is not None:
            row = (
                db.query(ExchangeTradingDay)
                .filter(
                    ExchangeTradingDay.exchange_id == exchange.id,
                    ExchangeTradingDay.trading_date == d,
                )
                .one_or_none()
            )
            if row is not None:
                return bool(row.is_trading_day)
    return d.weekday() < 5


def previous_trading_day(db: Session | None, d: date, *, exchange_code: str = "XNAS") -> date:
    cur = d - timedelta(days=1)
    for _ in range(14):
        if is_trading_day(db, cur, exchange_code=exchange_code):
            return cur
        cur -= timedelta(days=1)
    return d - timedelta(days=1)


def next_trading_day(db: Session | None, d: date, *, exchange_code: str = "XNAS") -> date:
    cur = d + timedelta(days=1)
    for _ in range(14):
        if is_trading_day(db, cur, exchange_code=exchange_code):
            return cur
        cur += timedelta(days=1)
    return d + timedelta(days=1)


def market_close_et(d: date) -> datetime:
    return datetime(d.year, d.month, d.day, 16, 0, tzinfo=_NY)


def eod_ready_after(d: date, *, lag_minutes: int = 90) -> datetime:
    return market_close_et(d) + timedelta(minutes=lag_minutes)


def latest_completed_session(
    db: Session | None,
    as_of: datetime | None = None,
    *,
    lag_minutes: int = 90,
    exchange_code: str = "XNAS",
) -> date:
    now = as_of or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    today = us_market_date(now)
    if is_trading_day(db, today, exchange_code=exchange_code):
        ready_at = eod_ready_after(today, lag_minutes=lag_minutes)
        if now.astimezone(timezone.utc) >= ready_at.astimezone(timezone.utc):
            return today
        return previous_trading_day(db, today, exchange_code=exchange_code)
    return previous_trading_day(db, today, exchange_code=exchange_code)


def next_expected_refresh(
    db: Session | None,
    market_date: date,
    *,
    lag_minutes: int = 90,
    exchange_code: str = "XNAS",
) -> datetime:
    nxt = next_trading_day(db, market_date, exchange_code=exchange_code)
    return eod_ready_after(nxt, lag_minutes=lag_minutes)
