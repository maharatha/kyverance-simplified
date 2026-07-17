from __future__ import annotations

from kyverance.config import Settings, get_settings
from kyverance.connectors.fake_provider import FakePlaidProvider
from kyverance.connectors.plaid_provider import RealPlaidProvider
from kyverance.connectors.provider_base import PlaidProvider
from kyverance.connectors.unavailable_provider import UnavailablePlaidProvider


def get_plaid_provider(settings: Settings | None = None) -> PlaidProvider:
    resolved = settings or get_settings()
    if resolved.plaid_configured:
        return RealPlaidProvider(resolved)
    # Local/test only: deterministic fake provider when credentials are unset.
    if resolved.is_local_or_test:
        return FakePlaidProvider()
    return UnavailablePlaidProvider()
