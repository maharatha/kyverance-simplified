"""Decimal-string API contracts for portfolios and wallets."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class PortfolioCreateIn(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    description: str | None = Field(default=None, max_length=2000)


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


class PortfolioSummaryOut(BaseModel):
    id: str
    name: str
    description: str | None = None
    visibility: str
    provenance: str
    status: str
    currency_code: str
    cash_balance: str
    created_at: datetime
    updated_at: datetime


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
