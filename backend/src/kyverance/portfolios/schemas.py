"""Decimal-string API contracts for portfolios, versions, and forks."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class PortfolioCreateIn(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    description: str | None = Field(default=None, max_length=2000)
    thesis: str | None = Field(default=None, max_length=8000)
    agent_config_ref: str | None = Field(default=None, max_length=128)


class PortfolioPatchIn(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    description: str | None = Field(default=None, max_length=2000)
    thesis: str | None = Field(default=None, max_length=8000)
    agent_config_ref: str | None = Field(default=None, max_length=128)


class LedgerEntryOut(BaseModel):
    id: str
    amount: str
    currency_code: str
    source_type: str
    funding_bucket: str
    reason: str | None = None
    actor: str
    created_at: datetime
    idempotency_key: str | None = None


class WalletOut(BaseModel):
    id: str
    cash_balance: str
    complimentary_balance: str
    currency_code: str
    version: int


class ForkLineageOut(BaseModel):
    id: str
    source_portfolio_id: str
    source_version_id: str
    license: str
    entitlement: str
    sync_enabled: bool
    mirror_trades: bool
    forked_at: datetime


class PortfolioSummaryOut(BaseModel):
    id: str
    name: str
    description: str | None = None
    thesis: str | None = None
    agent_config_ref: str | None = None
    visibility: str
    provenance: str
    status: str
    currency_code: str
    cash_balance: str
    created_at: datetime
    updated_at: datetime
    fork_lineage: ForkLineageOut | None = None


class PortfolioDetailOut(PortfolioSummaryOut):
    wallet: WalletOut
    ledger: list[LedgerEntryOut] = Field(default_factory=list)
    simulation_notice: str = (
        "Simulated portfolio with virtual cash. Not a brokerage account. "
        "Ledger entries are the source of cash truth."
    )


class PortfolioListOut(BaseModel):
    portfolios: list[PortfolioSummaryOut] = Field(default_factory=list)
    empty_state: str


class PortfolioVersionCreateIn(BaseModel):
    """Optional note; snapshot content is taken from the live portfolio."""

    note: str | None = Field(default=None, max_length=500)


class PortfolioVersionPublishIn(BaseModel):
    visibility: str = Field(description="private or public")
    license: str = Field(description="view_only or public_fork_allowed")
    provenance: str = Field(default="simulated")
    consent_acknowledged: bool
    disclosure_acknowledged: bool = True


class ForkCreateIn(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)


class HoldingSnapshotOut(BaseModel):
    symbol: str
    quantity: str
    avg_cost: str


class PortfolioVersionOut(BaseModel):
    id: str
    portfolio_id: str
    version_number: int
    name: str
    description: str | None = None
    thesis: str | None = None
    agent_config_ref: str | None = None
    holdings: list[HoldingSnapshotOut] = Field(default_factory=list)
    allocation: dict[str, Any] = Field(default_factory=dict)
    data_context: dict[str, Any] = Field(default_factory=dict)
    checksum: str
    status: str
    visibility: str
    provenance: str
    license: str | None = None
    disclosure: str | None = None
    consent_acknowledged: bool
    consent_text_version: str | None = None
    consent_at: datetime | None = None
    published_at: datetime | None = None
    created_at: datetime
    fork_allowed: bool = False
    fork_notice: str | None = None


class PortfolioVersionListOut(BaseModel):
    versions: list[PortfolioVersionOut] = Field(default_factory=list)
