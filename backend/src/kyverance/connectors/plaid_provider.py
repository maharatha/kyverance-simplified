"""Live Plaid SDK wrapper — only constructed when credentials are configured."""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any

from fastapi import HTTPException, status

from kyverance.config import Settings
from kyverance.connectors.constants import PROVIDER_MODE_PLAID
from kyverance.connectors.provider_base import (
    ExchangeResult,
    RemoteAccount,
    RemoteHolding,
    remote_account_from_plaid_dict,
)

logger = logging.getLogger(__name__)


def _env_host(env: str):
    import plaid

    normalized = (env or "sandbox").strip().lower()
    if normalized == "production":
        return plaid.Environment.Production
    return plaid.Environment.Sandbox


class RealPlaidProvider:
    mode = PROVIDER_MODE_PLAID

    def __init__(self, settings: Settings) -> None:
        if not settings.plaid_configured:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Plaid is not configured",
            )
        try:
            import plaid
            from plaid.api import plaid_api
        except ImportError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Plaid SDK is not installed",
            ) from exc

        configuration = plaid.Configuration(
            host=_env_host(settings.plaid_env),
            api_key={
                "clientId": settings.plaid_client_id,
                "secret": settings.plaid_api_secret,
            },
        )
        self._settings = settings
        self._api = plaid_api.PlaidApi(plaid.ApiClient(configuration))

    def create_link_token(self, *, client_user_id: str) -> str:
        import plaid
        from plaid.model.country_code import CountryCode
        from plaid.model.link_token_create_request import LinkTokenCreateRequest
        from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
        from plaid.model.products import Products

        user_kwargs: dict[str, Any] = {"client_user_id": client_user_id[:64]}
        if _env_host(self._settings.plaid_env) == __import__("plaid").Environment.Sandbox:
            user_kwargs["phone_number"] = "+14155550010"

        request = LinkTokenCreateRequest(
            products=[Products("transactions")],
            required_if_supported_products=[Products("investments")],
            client_name="Kyverance",
            country_codes=[CountryCode("US")],
            language="en",
            user=LinkTokenCreateRequestUser(**user_kwargs),
        )
        try:
            response = self._api.link_token_create(request)
        except plaid.ApiException as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=self._plaid_error_detail(exc),
            ) from exc

        token = getattr(response, "link_token", None) or response.to_dict().get("link_token")
        if not token:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Plaid did not return a link_token",
            )
        return str(token)

    def exchange_public_token(self, public_token: str) -> ExchangeResult:
        import plaid
        from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest

        try:
            response = self._api.item_public_token_exchange(
                ItemPublicTokenExchangeRequest(public_token=public_token)
            )
        except plaid.ApiException as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=self._plaid_error_detail(exc),
            ) from exc

        data = response.to_dict() if hasattr(response, "to_dict") else dict(response)
        access_token = data.get("access_token") or getattr(response, "access_token", None)
        item_id = data.get("item_id") or getattr(response, "item_id", None)
        if not access_token or not item_id:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Plaid token exchange failed",
            )
        return ExchangeResult(access_token=str(access_token), item_id=str(item_id))

    def get_accounts(self, access_token: str) -> list[RemoteAccount]:
        from plaid.model.accounts_get_request import AccountsGetRequest

        response = self._api.accounts_get(AccountsGetRequest(access_token=access_token))
        data = response.to_dict() if hasattr(response, "to_dict") else dict(response)
        accounts: list[RemoteAccount] = []
        for raw in data.get("accounts") or []:
            if isinstance(raw, dict):
                parsed = remote_account_from_plaid_dict(raw)
                if parsed:
                    accounts.append(parsed)
        return accounts

    def get_holdings(self, access_token: str) -> list[RemoteHolding]:
        from plaid.model.investments_holdings_get_request import InvestmentsHoldingsGetRequest

        try:
            response = self._api.investments_holdings_get(
                InvestmentsHoldingsGetRequest(access_token=access_token)
            )
        except Exception as exc:  # noqa: BLE001
            logger.info("Plaid investments_holdings_get unavailable: %s", type(exc).__name__)
            return []

        data = response.to_dict() if hasattr(response, "to_dict") else dict(response)
        securities = {
            str(sec.get("security_id")): sec
            for sec in (data.get("securities") or [])
            if isinstance(sec, dict) and sec.get("security_id")
        }
        holdings: list[RemoteHolding] = []
        for raw in data.get("holdings") or []:
            if not isinstance(raw, dict):
                continue
            account_id = str(raw.get("account_id") or "")
            security_id = str(raw.get("security_id") or "")
            if not account_id or not security_id:
                continue
            security = securities.get(security_id, {})
            symbol = security.get("ticker_symbol")
            name = security.get("name")
            try:
                quantity = Decimal(str(raw.get("quantity") or "0"))
            except Exception:
                continue
            currency = str(raw.get("iso_currency_code") or security.get("iso_currency_code") or "USD")
            holdings.append(
                RemoteHolding(
                    external_account_id=account_id,
                    external_security_id=security_id,
                    symbol=str(symbol)[:32] if symbol else None,
                    name=str(name)[:256] if name else None,
                    quantity=quantity,
                    currency=currency[:8],
                )
            )
        return holdings

    def get_institution_name(self, access_token: str) -> str | None:
        from plaid.model.accounts_get_request import AccountsGetRequest
        from plaid.model.country_code import CountryCode
        from plaid.model.institutions_get_by_id_request import InstitutionsGetByIdRequest

        response = self._api.accounts_get(AccountsGetRequest(access_token=access_token))
        data = response.to_dict() if hasattr(response, "to_dict") else dict(response)
        item = data.get("item") if isinstance(data.get("item"), dict) else {}
        institution_id = str(item.get("institution_id") or "")
        if not institution_id:
            return None
        try:
            inst_response = self._api.institutions_get_by_id(
                InstitutionsGetByIdRequest(institution_id=institution_id, country_codes=[CountryCode("US")])
            )
            inst_data = inst_response.to_dict() if hasattr(inst_response, "to_dict") else dict(inst_response)
            institution = inst_data.get("institution") if isinstance(inst_data.get("institution"), dict) else {}
            name = institution.get("name")
            return str(name) if name else None
        except Exception:
            return None

    def remove_item(self, access_token: str) -> None:
        from plaid.model.item_remove_request import ItemRemoveRequest

        try:
            self._api.item_remove(ItemRemoveRequest(access_token=access_token))
        except Exception as exc:  # noqa: BLE001
            logger.info("Plaid item_remove failed: %s", type(exc).__name__)

    @staticmethod
    def _plaid_error_detail(exc: Exception) -> str:
        try:
            import json

            body = getattr(exc, "body", None)
            raw = body if isinstance(body, str) else str(body or exc)
            parsed = json.loads(raw)
            code = parsed.get("error_code") or "PLAID_ERROR"
            message = parsed.get("error_message") or raw
            return f"{code}: {message}"
        except Exception:
            return "Plaid error"
