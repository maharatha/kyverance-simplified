"""Evidence collection from MRKT-01 internal market data only. No live providers."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from kyverance.market_data.models import (
    DailyPrice,
    Instrument,
    InstrumentListing,
    LatestDailyPrice,
    MarketExchange,
)
from kyverance.market_data.service import InternalDataUnavailable, get_latest_by_symbol


@dataclass
class EvidenceBundle:
    ticker: str
    exchange: str
    market_date: date
    instrument_id: UUID | None
    listing_id: UUID | None
    close: Decimal | None
    prior_close: Decimal | None
    volume: int | None
    history: list[dict[str, Any]] = field(default_factory=list)
    instrument_name: str | None = None
    data_mode: str = "end_of_day"
    provider_name: str = "internal_market_data"
    provenance: dict[str, Any] = field(default_factory=dict)
    source_data_timestamp: datetime | None = None
    gaps: list[str] = field(default_factory=list)

    def evidence_hash(self) -> str:
        payload = {
            "ticker": self.ticker,
            "exchange": self.exchange,
            "market_date": self.market_date.isoformat(),
            "close": str(self.close) if self.close is not None else None,
            "prior_close": str(self.prior_close) if self.prior_close is not None else None,
            "volume": self.volume,
            "history_len": len(self.history),
            "history_tail": self.history[-3:] if self.history else [],
            "data_mode": self.data_mode,
            "provider_name": self.provider_name,
            "gaps": sorted(self.gaps),
        }
        body = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
        return hashlib.sha256(body.encode("utf-8")).hexdigest()

    def available_evidence(self) -> set[str]:
        available: set[str] = set()
        if self.close is not None:
            available.add("eod_bar")
        if self.instrument_id is not None:
            available.add("instrument")
        if len(self.history) >= 2:
            available.add("history")
        if self.prior_close is not None:
            available.add("prior_close")
        return available


class EvidenceNotReady(Exception):
    """Internal market data missing or incomplete for research generation."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _resolve_listing(
    db: Session, *, ticker: str, exchange: str
) -> tuple[InstrumentListing, MarketExchange, Instrument]:
    ticker_u = ticker.upper().replace(".US", "")
    exchange_u = exchange.upper()
    codes = [exchange_u]
    if exchange_u == "US":
        codes = ["XNAS", "XNYS"]

    for code in codes:
        exchange_row = (
            db.query(MarketExchange)
            .filter(MarketExchange.canonical_code == code)
            .one_or_none()
        )
        if not exchange_row:
            continue
        listing = (
            db.query(InstrumentListing)
            .filter(
                InstrumentListing.exchange_id == exchange_row.id,
                InstrumentListing.ticker == ticker_u,
                InstrumentListing.is_active.is_(True),
            )
            .order_by(InstrumentListing.is_primary.desc())
            .first()
        )
        if listing is None:
            continue
        instrument = db.get(Instrument, listing.instrument_id)
        if instrument is None:
            continue
        return listing, exchange_row, instrument

    raise EvidenceNotReady("instrument_not_found", f"No active listing for {ticker_u}/{exchange_u}")


def collect_internal_evidence(
    db: Session,
    *,
    ticker: str,
    exchange: str = "XNAS",
    market_date: date | None = None,
    history_days: int = 20,
) -> EvidenceBundle:
    """Build grounded evidence from internal warehouse only."""
    listing, exchange_row, instrument = _resolve_listing(db, ticker=ticker, exchange=exchange)
    gaps: list[str] = []

    try:
        latest = get_latest_by_symbol(db, exchange_row.canonical_code, listing.ticker)
    except InternalDataUnavailable:
        gaps.append("latest_price")
        raise EvidenceNotReady(
            "market_data_not_ready",
            f"No published latest price for {listing.ticker}/{exchange_row.canonical_code}",
        )

    close = Decimal(str(latest["close"])) if latest.get("close") is not None else None
    volume = int(latest.get("volume") or 0)
    trading_date = date.fromisoformat(str(latest["tradingDate"]))
    if market_date is not None and trading_date != market_date:
        # Prefer exact market_date bar when available.
        day_row = (
            db.query(DailyPrice)
            .filter(
                DailyPrice.instrument_listing_id == listing.id,
                DailyPrice.trading_date == market_date,
            )
            .order_by(DailyPrice.data_version.desc())
            .first()
        )
        if day_row is None:
            gaps.append("exact_market_date")
            raise EvidenceNotReady(
                "market_data_not_ready",
                f"No daily bar for {listing.ticker} on {market_date.isoformat()}",
            )
        close = day_row.close
        volume = int(day_row.volume or 0)
        trading_date = day_row.trading_date

    history_rows = (
        db.query(DailyPrice)
        .filter(
            DailyPrice.instrument_listing_id == listing.id,
            DailyPrice.trading_date <= trading_date,
        )
        .order_by(DailyPrice.trading_date.desc())
        .limit(max(2, history_days))
        .all()
    )
    history = [
        {
            "tradingDate": r.trading_date.isoformat(),
            "close": str(r.close),
            "volume": int(r.volume or 0),
            "dataVersion": int(r.data_version or 1),
        }
        for r in reversed(history_rows)
    ]
    if len(history) < 2:
        gaps.append("history")

    prior_close: Decimal | None = None
    if len(history_rows) >= 2:
        prior_close = history_rows[1].close
    else:
        gaps.append("prior_close")

    data_mode = "end_of_day"
    if latest.get("isStale"):
        gaps.append("stale_price")

    source_ts = datetime.now(timezone.utc)
    if latest.get("updatedAt"):
        try:
            source_ts = datetime.fromisoformat(str(latest["updatedAt"]).replace("Z", "+00:00"))
        except ValueError:
            pass

    return EvidenceBundle(
        ticker=listing.ticker.upper(),
        exchange=exchange_row.canonical_code.upper(),
        market_date=trading_date,
        instrument_id=instrument.id,
        listing_id=listing.id,
        close=close,
        prior_close=prior_close,
        volume=volume,
        history=history,
        instrument_name=instrument.canonical_name,
        data_mode=data_mode,
        provider_name="internal_market_data",
        provenance={
            "instrument_id": str(instrument.id),
            "listing_id": str(listing.id),
            "provider_id": latest.get("providerId"),
            "data_status": latest.get("dataStatus"),
            "data_version": latest.get("dataVersion"),
            "availability": latest.get("availability"),
            "gaps": gaps,
            "plaid_excluded": True,
            "portfolio_excluded": True,
        },
        source_data_timestamp=source_ts,
        gaps=gaps,
    )
