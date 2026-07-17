"""Internal market-data reads — Postgres only. Never calls providers."""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import or_
from sqlalchemy.orm import Session

from kyverance.config import Settings, get_settings
from kyverance.market_data.models import (
    DailyPrice,
    Instrument,
    InstrumentListing,
    LatestDailyPrice,
    MarketExchange,
)

logger = logging.getLogger(__name__)


class InternalDataUnavailable(Exception):
    def __init__(self, message: str = "internal_data_unavailable") -> None:
        super().__init__(message)
        self.code = "internal_data_unavailable"


def _dec_str(v: Decimal | None) -> str | None:
    if v is None:
        return None
    return format(v, "f")


def _latest_payload(
    *,
    listing: InstrumentListing,
    exchange: MarketExchange,
    latest: LatestDailyPrice,
    instrument: Instrument | None,
    stale: bool,
) -> dict[str, Any]:
    return {
        "instrumentListingId": str(listing.id),
        "instrumentId": str(listing.instrument_id),
        "ticker": listing.ticker,
        "exchange": exchange.canonical_code,
        "currency": latest.currency_code,
        "tradingDate": latest.trading_date.isoformat(),
        "open": _dec_str(latest.open),
        "high": _dec_str(latest.high),
        "low": _dec_str(latest.low),
        "close": _dec_str(latest.close),
        "adjustedClose": _dec_str(latest.adjusted_close),
        "volume": int(latest.volume or 0),
        "dataStatus": latest.data_status,
        "dataVersion": int(latest.data_version or 1),
        "updatedAt": (latest.updated_at or datetime.now(timezone.utc)).isoformat(),
        "isStale": stale,
        "canonicalName": instrument.canonical_name if instrument else listing.ticker,
        "providerId": str(latest.provider_id) if latest.provider_id else None,
        "dataAsOf": latest.trading_date.isoformat(),
        "availability": "stale" if stale else "fresh",
    }


def _is_stale(latest: LatestDailyPrice, settings: Settings) -> bool:
    if not latest.updated_at:
        return True
    updated = latest.updated_at
    if updated.tzinfo is None:
        updated = updated.replace(tzinfo=timezone.utc)
    age = datetime.now(timezone.utc) - updated
    return age > timedelta(minutes=settings.market_data_stale_tolerance_minutes)


def get_latest_by_listing_id(
    db: Session, listing_id: UUID, settings: Settings | None = None
) -> dict[str, Any]:
    s = settings or get_settings()
    listing = db.get(InstrumentListing, listing_id)
    if not listing:
        raise InternalDataUnavailable("listing_not_found")
    latest = db.get(LatestDailyPrice, listing_id)
    if not latest:
        raise InternalDataUnavailable("latest_price_missing")
    exchange = db.get(MarketExchange, listing.exchange_id)
    if not exchange:
        raise InternalDataUnavailable("exchange_missing")
    instrument = db.get(Instrument, listing.instrument_id)
    return _latest_payload(
        listing=listing,
        exchange=exchange,
        latest=latest,
        instrument=instrument,
        stale=_is_stale(latest, s),
    )


def get_latest_by_symbol(
    db: Session, exchange_code: str, ticker: str, settings: Settings | None = None
) -> dict[str, Any]:
    s = settings or get_settings()
    exchange = (
        db.query(MarketExchange)
        .filter(MarketExchange.canonical_code == exchange_code.upper())
        .one_or_none()
    )
    if not exchange:
        if exchange_code.upper() == "US":
            for code in ("XNAS", "XNYS"):
                try:
                    return get_latest_by_symbol(db, code, ticker, s)
                except InternalDataUnavailable:
                    continue
        raise InternalDataUnavailable("exchange_not_found")

    listing = (
        db.query(InstrumentListing)
        .filter(
            InstrumentListing.exchange_id == exchange.id,
            InstrumentListing.ticker == ticker.upper(),
            InstrumentListing.is_active.is_(True),
        )
        .order_by(InstrumentListing.is_primary.desc())
        .first()
    )
    if not listing:
        raise InternalDataUnavailable("symbol_not_found")
    return get_latest_by_listing_id(db, listing.id, s)


def get_history(
    db: Session,
    listing_id: UUID,
    *,
    from_date: date,
    to_date: date,
    settings: Settings | None = None,
) -> dict[str, Any]:
    s = settings or get_settings()
    if to_date < from_date:
        raise ValueError("invalid_date_range")
    span = (to_date - from_date).days
    if span > s.market_data_max_history_days:
        raise ValueError("range_too_large")

    listing = db.get(InstrumentListing, listing_id)
    if not listing:
        raise InternalDataUnavailable("listing_not_found")
    latest = db.get(LatestDailyPrice, listing_id)
    version = int(latest.data_version) if latest else 1

    rows = (
        db.query(DailyPrice)
        .filter(
            DailyPrice.instrument_listing_id == listing_id,
            DailyPrice.trading_date >= from_date,
            DailyPrice.trading_date <= to_date,
        )
        .order_by(DailyPrice.trading_date.asc())
        .all()
    )
    if not rows:
        raise InternalDataUnavailable("history_missing")

    points = [
        {
            "tradingDate": r.trading_date.isoformat(),
            "open": _dec_str(r.open),
            "high": _dec_str(r.high),
            "low": _dec_str(r.low),
            "close": _dec_str(r.close),
            "adjustedClose": _dec_str(r.adjusted_close),
            "volume": int(r.volume or 0),
            "dataVersion": int(r.data_version or 1),
            "dataStatus": r.data_status,
            "providerId": str(r.provider_id) if r.provider_id else None,
        }
        for r in rows
    ]
    return {
        "instrumentListingId": str(listing_id),
        "from": from_date.isoformat(),
        "to": to_date.isoformat(),
        "points": points,
        "dataVersion": version,
    }


def get_history_by_symbol(
    db: Session,
    exchange_code: str,
    ticker: str,
    *,
    from_date: date,
    to_date: date,
    settings: Settings | None = None,
) -> dict[str, Any]:
    latest = get_latest_by_symbol(db, exchange_code, ticker, settings)
    return get_history(
        db,
        UUID(latest["instrumentListingId"]),
        from_date=from_date,
        to_date=to_date,
        settings=settings,
    )


def search_listings(db: Session, q: str, *, limit: int = 12) -> list[dict[str, Any]]:
    query = (q or "").strip().upper()
    if len(query) < 1:
        return []
    rows = (
        db.query(InstrumentListing, MarketExchange, Instrument)
        .join(MarketExchange, MarketExchange.id == InstrumentListing.exchange_id)
        .join(Instrument, Instrument.id == InstrumentListing.instrument_id)
        .filter(
            InstrumentListing.is_active.is_(True),
            MarketExchange.is_active.is_(True),
            or_(
                InstrumentListing.ticker.ilike(f"{query}%"),
                Instrument.canonical_name.ilike(f"%{query}%"),
            ),
        )
        .order_by((InstrumentListing.ticker != query), InstrumentListing.ticker.asc())
        .limit(limit)
        .all()
    )
    out: list[dict[str, Any]] = []
    for listing, exchange, instrument in rows:
        latest = db.get(LatestDailyPrice, listing.id)
        out.append(
            {
                "instrumentListingId": str(listing.id),
                "symbol": listing.ticker,
                "name": instrument.canonical_name,
                "exchange": exchange.canonical_code,
                "type": instrument.instrument_type,
                "price": _dec_str(latest.close) if latest else None,
            }
        )
    return out
