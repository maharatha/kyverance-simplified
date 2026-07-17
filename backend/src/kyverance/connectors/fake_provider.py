"""Deterministic fake Plaid provider for local/test verification without credentials."""

from __future__ import annotations

import hashlib
from decimal import Decimal

from fastapi import HTTPException, status

from kyverance.connectors.constants import PROVIDER_MODE_FAKE
from kyverance.connectors.provider_base import ExchangeResult, RemoteAccount, RemoteHolding


class FakePlaidProvider:
    mode = PROVIDER_MODE_FAKE

    def create_link_token(self, *, client_user_id: str) -> str:
        digest = hashlib.sha256(client_user_id.encode("utf-8")).hexdigest()[:16]
        return f"link-sandbox-fake-{digest}"

    def exchange_public_token(self, public_token: str) -> ExchangeResult:
        token = (public_token or "").strip()
        if not token.startswith("public-fake-") and not token.startswith("public-sandbox-fake-"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Fake provider only accepts public-fake-* tokens",
            )
        digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
        return ExchangeResult(
            access_token=f"access-sandbox-fake-{digest[:24]}",
            item_id=f"item-fake-{digest[24:40]}",
        )

    def get_accounts(self, access_token: str) -> list[RemoteAccount]:
        _ = access_token
        return [
            RemoteAccount(
                external_account_id="fake-acct-brokerage",
                name="Sample Brokerage",
                mask="0000",
                account_type="brokerage",
                currency="USD",
            ),
            RemoteAccount(
                external_account_id="fake-acct-ira",
                name="Sample IRA",
                mask="1111",
                account_type="ira",
                currency="USD",
            ),
        ]

    def get_holdings(self, access_token: str) -> list[RemoteHolding]:
        _ = access_token
        return [
            RemoteHolding(
                external_account_id="fake-acct-brokerage",
                external_security_id="fake-sec-voo",
                symbol="VOO",
                name="Vanguard S&P 500 ETF",
                quantity=Decimal("10.5"),
                currency="USD",
            ),
            RemoteHolding(
                external_account_id="fake-acct-ira",
                external_security_id="fake-sec-bnd",
                symbol="BND",
                name="Vanguard Total Bond Market ETF",
                quantity=Decimal("25"),
                currency="USD",
            ),
        ]

    def get_institution_name(self, access_token: str) -> str | None:
        _ = access_token
        return "Sample Bank (local fake)"

    def remove_item(self, access_token: str) -> None:
        _ = access_token
        return None
