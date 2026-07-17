"""Safe fixture quote mode — deterministic marks, never live brokerage data."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi import HTTPException, status

from kyverance.config import get_settings
from kyverance.simulation.constants import (
    DATA_MODE_FIXTURE,
    FIXTURE_QUOTES,
    FRESHNESS_FRESH,
    FRESHNESS_STALE,
    FRESHNESS_UNAVAILABLE,
    QUOTE_MAX_AGE_SECONDS,
)
from kyverance.simulation.money import money


@dataclass(frozen=True)
class Quote:
    symbol: str
    price: Decimal
    quote_id: str
    as_of: datetime
    received_at: datetime
    provider: str
    data_mode: str
    freshness_label: str
    age_seconds: int
    max_age_seconds: int


def _now() -> datetime:
    return datetime.now(timezone.utc)


def fetch_quote(symbol: str, *, now: datetime | None = None) -> Quote:
    """Return a quote. Local/test default is fixture mode only."""
    settings = get_settings()
    mode = (settings.quote_mode or DATA_MODE_FIXTURE).strip().lower()
    if mode != DATA_MODE_FIXTURE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Only fixture quote mode is enabled in this release",
        )
    return _fixture_quote(symbol, now=now or _now())


def _fixture_quote(symbol: str, *, now: datetime) -> Quote:
    sym = symbol.upper().strip()
    if not sym:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Symbol is required")
    price = FIXTURE_QUOTES.get(sym)
    if price is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported symbol for fixture quotes: {sym}",
        )
    # Fixture marks are authored as-of "now" so previews stay fresh in tests/local.
    as_of = now
    received_at = now
    age = max(0, int((received_at - as_of).total_seconds()))
    freshness = FRESHNESS_FRESH if age <= QUOTE_MAX_AGE_SECONDS else FRESHNESS_STALE
    return Quote(
        symbol=sym,
        price=money(price),
        quote_id=f"fixture:{sym}:{as_of.strftime('%Y%m%dT%H%M%SZ')}",
        as_of=as_of,
        received_at=received_at,
        provider="fixture",
        data_mode=DATA_MODE_FIXTURE,
        freshness_label=freshness,
        age_seconds=age,
        max_age_seconds=QUOTE_MAX_AGE_SECONDS,
    )


def require_fresh_quote(quote: Quote) -> None:
    if quote.freshness_label == FRESHNESS_UNAVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Quote unavailable — trading paused",
        )
    if quote.freshness_label == FRESHNESS_STALE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Quote is stale — request a new preview",
        )


def make_stale_quote(symbol: str, *, age_seconds: int = QUOTE_MAX_AGE_SECONDS + 60) -> Quote:
    """Test helper: fixture quote marked stale."""
    now = _now()
    as_of = now - timedelta(seconds=age_seconds)
    base = _fixture_quote(symbol, now=as_of)
    return Quote(
        symbol=base.symbol,
        price=base.price,
        quote_id=base.quote_id,
        as_of=as_of,
        received_at=now,
        provider=base.provider,
        data_mode=base.data_mode,
        freshness_label=FRESHNESS_STALE,
        age_seconds=age_seconds,
        max_age_seconds=QUOTE_MAX_AGE_SECONDS,
    )
