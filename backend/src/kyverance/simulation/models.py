"""Simulation wallet, ledger, order preview/confirm, positions, and receipts."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from kyverance.db.session import Base
from kyverance.simulation.constants import (
    FUNDING_BUCKET_COMPLIMENTARY,
    VIRTUAL_CURRENCY_CODE,
)

if TYPE_CHECKING:
    from kyverance.portfolios.models import Portfolio


# SQLite tests use JSON; Postgres migrations use JSONB via Alembic.
JsonType = JSON().with_variant(JSONB(), "postgresql")


class SimWallet(Base):
    """Isolated virtual wallet for exactly one portfolio.

    ``balance`` is a cached projection that must reconcile to the ledger sum.
    """

    __tablename__ = "sim_wallets"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    portfolio_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("portfolios.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    owner_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    currency_code: Mapped[str] = mapped_column(String(8), nullable=False, default=VIRTUAL_CURRENCY_CODE)
    balance: Mapped[Decimal] = mapped_column(Numeric(19, 4), nullable=False, default=Decimal("0"))
    complimentary_balance: Mapped[Decimal] = mapped_column(
        Numeric(19, 4), nullable=False, default=Decimal("0")
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    portfolio: Mapped[Portfolio] = relationship("Portfolio", back_populates="wallet")
    ledger_entries: Mapped[list[WalletLedgerEntry]] = relationship(
        "WalletLedgerEntry",
        back_populates="wallet",
        cascade="save-update, merge",
        lazy="selectin",
    )


class WalletLedgerEntry(Base):
    """Immutable debit/credit source record. Never update or delete rows."""

    __tablename__ = "wallet_ledger_entries"
    __table_args__ = (
        UniqueConstraint("wallet_id", "idempotency_key", name="uq_ledger_wallet_idem"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    wallet_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("sim_wallets.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )
    portfolio_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("portfolios.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    owner_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(19, 4), nullable=False)
    currency_code: Mapped[str] = mapped_column(String(8), nullable=False, default=VIRTUAL_CURRENCY_CODE)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    funding_bucket: Mapped[str] = mapped_column(
        String(32), nullable=False, default=FUNDING_BUCKET_COMPLIMENTARY
    )
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    reason: Mapped[str | None] = mapped_column(String(256), nullable=True)
    actor: Mapped[str] = mapped_column(String(64), nullable=False, default="system")
    # Soft link to sim_orders.id (no FK — avoids circular create order with ledger).
    related_order_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    wallet: Mapped[SimWallet] = relationship("SimWallet", back_populates="ledger_entries")


class OrderPreview(Base):
    """Server-authored market-order preview. Confirmation must bind to a current row."""

    __tablename__ = "order_previews"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    portfolio_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("portfolios.id", ondelete="CASCADE"), index=True, nullable=False
    )
    wallet_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("sim_wallets.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    owner_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    side: Mapped[str] = mapped_column(String(8), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(28, 10), nullable=False)
    notional: Mapped[Decimal] = mapped_column(Numeric(19, 4), nullable=False)
    quote_price: Mapped[Decimal] = mapped_column(Numeric(19, 4), nullable=False)
    execution_price: Mapped[Decimal] = mapped_column(Numeric(19, 4), nullable=False)
    slippage_bps: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    fee: Mapped[Decimal] = mapped_column(Numeric(19, 4), nullable=False, default=Decimal("0"))
    quote_id: Mapped[str] = mapped_column(String(128), nullable=False)
    quote_as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    quote_received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    freshness_label: Mapped[str] = mapped_column(String(32), nullable=False)
    data_mode: Mapped[str] = mapped_column(String(32), nullable=False)
    execution_policy: Mapped[str] = mapped_column(String(64), nullable=False)
    cash_after: Mapped[Decimal] = mapped_column(Numeric(19, 4), nullable=False)
    warnings_json: Mapped[list[Any]] = mapped_column(JsonType, nullable=False, default=list)
    request_fingerprint: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="open")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SimOrder(Base):
    """Terminal market order created only via explicit confirmation."""

    __tablename__ = "sim_orders"
    __table_args__ = (
        UniqueConstraint("owner_user_id", "idempotency_key", name="uq_sim_order_owner_idem"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    portfolio_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("portfolios.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    wallet_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("sim_wallets.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    owner_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    preview_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("order_previews.id", ondelete="RESTRICT"), unique=True, nullable=False
    )
    symbol: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    side: Mapped[str] = mapped_column(String(8), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(28, 10), nullable=False)
    notional: Mapped[Decimal] = mapped_column(Numeric(19, 4), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    request_fingerprint: Mapped[str] = mapped_column(String(128), nullable=False)
    quote_id: Mapped[str] = mapped_column(String(128), nullable=False)
    reject_reason: Mapped[str | None] = mapped_column(String(256), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    execution: Mapped[SimExecution | None] = relationship(
        "SimExecution", back_populates="order", uselist=False, lazy="selectin"
    )
    receipt: Mapped[OrderReceipt | None] = relationship(
        "OrderReceipt", back_populates="order", uselist=False, lazy="selectin"
    )


class SimExecution(Base):
    """Immutable simulated fill for a terminal order."""

    __tablename__ = "sim_executions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("sim_orders.id", ondelete="RESTRICT"), unique=True, nullable=False
    )
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    side: Mapped[str] = mapped_column(String(8), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(28, 10), nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(19, 4), nullable=False)
    notional: Mapped[Decimal] = mapped_column(Numeric(19, 4), nullable=False)
    fee: Mapped[Decimal] = mapped_column(Numeric(19, 4), nullable=False, default=Decimal("0"))
    slippage_bps: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False, default=Decimal("0"))
    quote_id: Mapped[str] = mapped_column(String(128), nullable=False)
    quote_as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    quote_received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    freshness_label: Mapped[str] = mapped_column(String(32), nullable=False)
    data_mode: Mapped[str] = mapped_column(String(32), nullable=False)
    execution_policy: Mapped[str] = mapped_column(String(64), nullable=False)
    simulated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    order: Mapped[SimOrder] = relationship("SimOrder", back_populates="execution")


class SimPosition(Base):
    """Projected holdings per portfolio/symbol. Lots are the quantity source of truth."""

    __tablename__ = "sim_positions"
    __table_args__ = (UniqueConstraint("portfolio_id", "symbol", name="uq_sim_pos_symbol"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    portfolio_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("portfolios.id", ondelete="CASCADE"), index=True, nullable=False
    )
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(28, 10), nullable=False, default=Decimal("0"))
    avg_cost: Mapped[Decimal] = mapped_column(Numeric(19, 4), nullable=False, default=Decimal("0"))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class SimPositionLot(Base):
    """FIFO lot opened by a buy execution."""

    __tablename__ = "sim_position_lots"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    portfolio_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("portfolios.id", ondelete="CASCADE"), index=True, nullable=False
    )
    symbol: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    quantity_remaining: Mapped[Decimal] = mapped_column(Numeric(28, 10), nullable=False)
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(19, 4), nullable=False)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    # Nullable for FORK-01 seed lots that have no simulated execution.
    execution_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("sim_executions.id", ondelete="RESTRICT"), nullable=True
    )


class OrderReceipt(Base):
    """Immutable activity/receipt projection created with the order transaction."""

    __tablename__ = "order_receipts"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("sim_orders.id", ondelete="RESTRICT"), unique=True, nullable=False
    )
    portfolio_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("portfolios.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    owner_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    payload_json: Mapped[dict[str, Any]] = mapped_column(JsonType, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    order: Mapped[SimOrder] = relationship("SimOrder", back_populates="receipt")


class ReconciliationIncident(Base):
    """Audit incident when cash or quantity projections diverge from sources."""

    __tablename__ = "reconciliation_incidents"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    portfolio_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("portfolios.id", ondelete="CASCADE"), index=True, nullable=False
    )
    owner_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    kind: Mapped[str] = mapped_column(String(64), nullable=False)
    detail: Mapped[str] = mapped_column(Text, nullable=False)
    snapshot_json: Mapped[dict[str, Any]] = mapped_column(JsonType, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
