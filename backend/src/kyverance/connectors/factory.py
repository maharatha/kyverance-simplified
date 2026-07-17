from __future__ import annotations

from kyverance.config import Settings, get_settings
from kyverance.connectors.fake_provider import FakePlaidProvider
from kyverance.connectors.plaid_provider import RealPlaidProvider
from kyverance.connectors.provider_base import PlaidProvider


def get_plaid_provider(settings: Settings | None = None) -> PlaidProvider:
    resolved = settings or get_settings()
    if resolved.plaid_configured:
        return RealPlaidProvider(resolved)
    return FakePlaidProvider()
