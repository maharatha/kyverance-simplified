"""Resolve market-data provider. Default is deterministic fake."""

from __future__ import annotations

from kyverance.config import Settings, get_settings
from kyverance.market_data.constants import PROVIDER_FAKE, PROVIDER_LIVE
from kyverance.market_data.providers.base import MarketDataProvider
from kyverance.market_data.providers.fake import FakeMarketDataProvider


def get_market_data_provider(settings: Settings | None = None) -> MarketDataProvider:
    s = settings or get_settings()
    code = (s.market_data_provider or PROVIDER_FAKE).strip().lower()
    if code in {PROVIDER_LIVE, "eodhd", "production"}:
        from kyverance.market_data.providers.live_disabled import DisabledLiveMarketDataProvider

        return DisabledLiveMarketDataProvider(s)
    return FakeMarketDataProvider()
