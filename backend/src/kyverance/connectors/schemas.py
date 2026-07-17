from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class PlaidConsentIn(BaseModel):
    granted: bool = True


class PlaidLinkTokenOut(BaseModel):
    link_token: str
    mode: str
    expiration_hint: str | None = None


class PlaidExchangeIn(BaseModel):
    public_token: str = Field(min_length=8, max_length=512)
    provider_key: str = Field(default="any", max_length=64)


class PlaidHoldingOut(BaseModel):
    id: str
    symbol: str | None = None
    name: str | None = None
    quantity: Decimal
    currency: str
    provenance: str
    source_label: str


class PlaidAccountOut(BaseModel):
    id: str
    connection_id: str
    name: str
    mask: str | None = None
    account_type: str | None = None
    currency: str
    provenance: str
    source_label: str
    last_synced_at: datetime | None = None
    holdings: list[PlaidHoldingOut] = Field(default_factory=list)


class PlaidConnectionOut(BaseModel):
    id: str
    provider_key: str
    institution_name: str | None = None
    status: str
    last_synced_at: datetime | None = None
    consent_recorded_at: datetime | None = None
    disconnected_at: datetime | None = None
    deletion_requested_at: datetime | None = None
    accounts: list[PlaidAccountOut] = Field(default_factory=list)


class ConnectorsOverviewOut(BaseModel):
    configured: bool
    plaid_configured: bool
    mode: str
    connect_consent_granted: bool
    data_retention_consent_granted: bool
    empty_state: str
    connections: list[PlaidConnectionOut] = Field(default_factory=list)
    message: str | None = None


class DeletionRequestOut(BaseModel):
    id: str
    connection_id: str
    status: str
    requested_at: datetime
