"""Simulation wallet and immutable ledger — source of cash truth per portfolio."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from kyverance.db.session import Base
from kyverance.simulation.constants import (
    FUNDING_BUCKET_COMPLIMENTARY,
    VIRTUAL_CURRENCY_CODE,
)

if TYPE_CHECKING:
    from kyverance.portfolios.models import Portfolio


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
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    wallet: Mapped[SimWallet] = relationship("SimWallet", back_populates="ledger_entries")
