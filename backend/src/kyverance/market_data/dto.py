"""Provider-neutral domain DTOs (not ORM)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Any


@dataclass(frozen=True)
class ProviderExchange:
    provider_code: str
    name: str
    country_code: str = "US"
    currency_code: str = "USD"
    mic_hint: str | None = None
    timezone: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ProviderInstrument:
    provider_symbol: str
    provider_exchange_code: str
    name: str
    instrument_type: str = "equity"
    currency_code: str = "USD"
    isin: str | None = None
    is_active: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ProviderDailyPrice:
    provider_symbol: str
    provider_exchange_code: str
    trading_date: date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    adjusted_close: Decimal | None = None
    volume: int = 0
    currency_code: str = "USD"
    source_updated_at: datetime | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class NormalizedDailyPrice:
    instrument_listing_id: str
    trading_date: date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    adjusted_close: Decimal | None
    volume: int
    currency_code: str
    provider_symbol: str
    provider_exchange_code: str
    source_updated_at: datetime | None = None


@dataclass
class ValidationIssue:
    error_type: str
    message: str
    provider_record_identifier: str | None = None
    raw_record: dict[str, Any] | None = None
    severity: str = "error"  # error | warning
