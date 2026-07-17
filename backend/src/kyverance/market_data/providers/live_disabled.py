"""Live provider adapter port — disabled unless explicitly configured.

MRKT-01 does not ship a working live HTTP client. Selecting live without a
token raises; secrets are never logged or persisted.
"""

from __future__ import annotations

from kyverance.config import Settings
from kyverance.market_data.dto import ProviderDailyPrice, ProviderExchange, ProviderInstrument
from kyverance.market_data.providers.base import ProviderNotConfiguredError


class DisabledLiveMarketDataProvider:
    """Placeholder for a future live vendor adapter (EODHD / Twelve Data)."""

    code = "live"

    def __init__(self, settings: Settings) -> None:
        token = (settings.market_data_live_api_token or "").strip()
        if not token:
            raise ProviderNotConfiguredError(
                "Live market-data provider selected but MARKET_DATA_LIVE_API_TOKEN is unset. "
                "Use MARKET_DATA_PROVIDER=fake for local/CI."
            )
        # Token accepted only to prove configuration gate; never stored on self.
        _ = token
        raise ProviderNotConfiguredError(
            "Live market-data HTTP adapter is not enabled in this slice. "
            "Keep MARKET_DATA_PROVIDER=fake."
        )

    async def get_exchanges(self) -> list[ProviderExchange]:
        raise ProviderNotConfiguredError("live provider disabled")

    async def get_instruments(self, exchange_code: str) -> list[ProviderInstrument]:
        _ = exchange_code
        raise ProviderNotConfiguredError("live provider disabled")

    async def get_exchange_eod(
        self, exchange_code: str, trading_date: str
    ) -> list[ProviderDailyPrice]:
        _ = exchange_code, trading_date
        raise ProviderNotConfiguredError("live provider disabled")

    async def get_historical_prices(
        self, provider_symbol: str, from_date: str, to_date: str
    ) -> list[ProviderDailyPrice]:
        _ = provider_symbol, from_date, to_date
        raise ProviderNotConfiguredError("live provider disabled")
