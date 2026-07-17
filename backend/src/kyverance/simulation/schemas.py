"""Decimal-string API contracts for simulated order preview/confirm/receipt."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Self

from pydantic import BaseModel, Field, model_validator


class OrderPreviewIn(BaseModel):
    symbol: str = Field(min_length=1, max_length=32)
    side: str = Field(min_length=3, max_length=8)
    quantity: str | None = None
    notional: str | None = None

    @model_validator(mode="after")
    def exactly_one_size(self) -> Self:
        if (self.quantity is None) == (self.notional is None):
            raise ValueError("Provide exactly one of quantity or notional")
        return self


class OrderConfirmIn(BaseModel):
    preview_id: str = Field(min_length=1, max_length=64)


class QuoteMetaOut(BaseModel):
    quote_id: str
    quote_as_of: datetime
    quote_received_at: datetime
    provider: str
    freshness_label: str
    data_mode: str
    execution_policy: str


class OrderPreviewOut(BaseModel):
    preview_id: str
    portfolio_id: str
    wallet_id: str
    symbol: str
    side: str
    quantity: str
    notional: str
    quote_price: str
    execution_price: str
    slippage_bps: str
    fee: str
    cash_after: str
    warnings: list[str] = Field(default_factory=list)
    expires_at: datetime
    status: str
    quote: QuoteMetaOut
    disclosure: str


class OrderReceiptOut(BaseModel):
    receipt_id: str
    order_id: str
    request_id: str
    portfolio_id: str
    status: str
    symbol: str
    side: str
    quantity: str
    notional: str
    execution_price: str
    fee: str
    slippage_bps: str
    ledger_entry_ids: list[str] = Field(default_factory=list)
    position_quantity: str
    position_delta: str
    cash_balance: str
    quote: QuoteMetaOut
    simulated_at: datetime | None = None
    disclosure: str
    created_at: datetime | None = None


class ActivityItemOut(BaseModel):
    receipt_id: str
    order_id: str
    symbol: str
    side: str
    status: str
    quantity: str
    notional: str
    created_at: datetime
    disclosure: str


class ActivityListOut(BaseModel):
    items: list[ActivityItemOut] = Field(default_factory=list)


class PositionOut(BaseModel):
    symbol: str
    quantity: str
    avg_cost: str


class PositionsListOut(BaseModel):
    positions: list[PositionOut] = Field(default_factory=list)


class ReconciliationCashOut(BaseModel):
    ledger_sum: str
    cached_balance: str
    complimentary_balance: str
    ok: bool
    delta: str


class ReconciliationPositionOut(BaseModel):
    symbol: str
    position_quantity: str
    lots_sum: str
    ok: bool


class ReconciliationOut(BaseModel):
    portfolio_id: str
    wallet_id: str
    ok: bool
    cash: ReconciliationCashOut
    positions: list[ReconciliationPositionOut] = Field(default_factory=list)
    orphan_lot_symbols: list[str] = Field(default_factory=list)
    positions_ok: bool
