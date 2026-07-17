from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Protocol


@dataclass(frozen=True)
class ExchangeResult:
    access_token: str
    item_id: str


@dataclass(frozen=True)
class RemoteAccount:
    external_account_id: str
    name: str
    mask: str | None
    account_type: str | None
    currency: str


@dataclass(frozen=True)
class RemoteHolding:
    external_account_id: str
    external_security_id: str
    symbol: str | None
    name: str | None
    quantity: Decimal
    currency: str


class PlaidProvider(Protocol):
    mode: str

    def create_link_token(self, *, client_user_id: str) -> str: ...

    def exchange_public_token(self, public_token: str) -> ExchangeResult: ...

    def get_accounts(self, access_token: str) -> list[RemoteAccount]: ...

    def get_holdings(self, access_token: str) -> list[RemoteHolding]: ...

    def get_institution_name(self, access_token: str) -> str | None: ...

    def remove_item(self, access_token: str) -> None: ...


def remote_account_from_plaid_dict(raw: dict[str, Any]) -> RemoteAccount | None:
    external_id = str(raw.get("account_id") or "").strip()
    if not external_id:
        return None
    name = str(raw.get("name") or raw.get("official_name") or "Account")
    mask = raw.get("mask")
    subtype = raw.get("subtype") or raw.get("type")
    balances = raw.get("balances") if isinstance(raw.get("balances"), dict) else {}
    currency = str(balances.get("iso_currency_code") or "USD")
    return RemoteAccount(
        external_account_id=external_id,
        name=name[:256],
        mask=str(mask)[:16] if mask is not None else None,
        account_type=str(subtype)[:64] if subtype is not None else None,
        currency=currency[:8],
    )
