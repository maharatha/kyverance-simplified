"""Provider-neutral market-data ingestion protocol. Ingest workers only."""

from __future__ import annotations

from typing import Protocol

from kyverance.market_data.dto import ProviderDailyPrice, ProviderExchange, ProviderInstrument


class MarketDataProvider(Protocol):
    @property
    def code(self) -> str: ...

    async def get_exchanges(self) -> list[ProviderExchange]: ...

    async def get_instruments(self, exchange_code: str) -> list[ProviderInstrument]: ...

    async def get_exchange_eod(
        self, exchange_code: str, trading_date: str
    ) -> list[ProviderDailyPrice]: ...

    async def get_historical_prices(
        self, provider_symbol: str, from_date: str, to_date: str
    ) -> list[ProviderDailyPrice]: ...


class ProviderNotConfiguredError(RuntimeError):
    """Raised when a live provider is selected without credentials."""
