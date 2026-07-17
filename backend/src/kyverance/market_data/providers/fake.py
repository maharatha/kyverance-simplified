"""Deterministic fake provider for local/CI ingest. No network, no secrets."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from kyverance.market_data.dto import ProviderDailyPrice, ProviderExchange, ProviderInstrument


def _d(s: str) -> date:
    return date.fromisoformat(s)


class FakeMarketDataProvider:
    code = "fake"

    def __init__(self) -> None:
        self._instruments = [
            ProviderInstrument("AAPL", "US", "Apple Inc.", isin="US0378331005"),
            ProviderInstrument("MSFT", "US", "Microsoft Corporation", isin="US5949181045"),
            ProviderInstrument("GOOGL", "US", "Alphabet Inc."),
        ]
        base = _d("2026-07-01")
        self._prices: list[ProviderDailyPrice] = []
        for i in range(10):
            d = base + timedelta(days=i)
            if d.weekday() >= 5:
                continue
            for sym, close0 in (
                ("AAPL", Decimal("210.00")),
                ("MSFT", Decimal("450.00")),
                ("GOOGL", Decimal("180.00")),
            ):
                close = close0 + Decimal(i)
                self._prices.append(
                    ProviderDailyPrice(
                        provider_symbol=sym,
                        provider_exchange_code="US",
                        trading_date=d,
                        open=close - Decimal("1"),
                        high=close + Decimal("2"),
                        low=close - Decimal("2"),
                        close=close,
                        adjusted_close=close,
                        volume=1_000_000 + i * 1000,
                        source_updated_at=datetime(d.year, d.month, d.day, 20, 0, tzinfo=timezone.utc),
                    )
                )

    async def get_exchanges(self) -> list[ProviderExchange]:
        return [
            ProviderExchange(
                "US", "USA Stocks", "US", "USD", mic_hint="XNAS", timezone="America/New_York"
            ),
        ]

    async def get_instruments(self, exchange_code: str) -> list[ProviderInstrument]:
        _ = exchange_code
        return list(self._instruments)

    async def get_exchange_eod(self, exchange_code: str, trading_date: str) -> list[ProviderDailyPrice]:
        _ = exchange_code
        d = _d(trading_date)
        return [p for p in self._prices if p.trading_date == d]

    async def get_historical_prices(
        self, provider_symbol: str, from_date: str, to_date: str
    ) -> list[ProviderDailyPrice]:
        a, b = _d(from_date), _d(to_date)
        return [
            p
            for p in self._prices
            if p.provider_symbol == provider_symbol.upper() and a <= p.trading_date <= b
        ]
