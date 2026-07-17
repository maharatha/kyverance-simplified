"""No-op provider when Plaid is unset outside local/test — overview stays HTTP 200."""

from __future__ import annotations

from fastapi import HTTPException, status

from kyverance.connectors.constants import PROVIDER_MODE_UNAVAILABLE
from kyverance.connectors.provider_base import ExchangeResult, RemoteAccount, RemoteHolding

_DETAIL = "Plaid is not configured"


class UnavailablePlaidProvider:
    mode = PROVIDER_MODE_UNAVAILABLE

    def create_link_token(self, *, client_user_id: str) -> str:
        _ = client_user_id
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=_DETAIL)

    def exchange_public_token(self, public_token: str) -> ExchangeResult:
        _ = public_token
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=_DETAIL)

    def get_accounts(self, access_token: str) -> list[RemoteAccount]:
        _ = access_token
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=_DETAIL)

    def get_holdings(self, access_token: str) -> list[RemoteHolding]:
        _ = access_token
        return []

    def get_institution_name(self, access_token: str) -> str | None:
        _ = access_token
        return None

    def remove_item(self, access_token: str) -> None:
        _ = access_token
        return None
