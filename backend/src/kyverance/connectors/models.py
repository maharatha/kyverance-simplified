from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from kyverance.connectors.constants import (
    CONNECTION_STATUS_CONNECTED,
    PROVENANCE_PLAID_READ_ONLY,
    SOURCE_LABEL_PLAID,
)
from kyverance.db.session import Base


class PlaidConnection(Base):
    """Owner-scoped Plaid Item connection with encrypted/token-reference-ready storage."""

    __tablename__ = "plaid_connections"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    item_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    # Ciphertext of the Plaid access token — never return to clients or log.
    access_token_ciphertext: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Future Key Vault / secret-store reference when ciphertext is vacated.
    token_vault_ref: Mapped[str | None] = mapped_column(String(256), nullable=True)
    encryption_kid: Mapped[str | None] = mapped_column(String(64), nullable=True)
    provider_key: Mapped[str] = mapped_column(String(64), nullable=False, default="any")
    institution_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=CONNECTION_STATUS_CONNECTED)
    consent_recorded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    disconnected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deletion_requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    accounts: Mapped[list[PlaidAccount]] = relationship(
        back_populates="connection", cascade="all, delete-orphan", lazy="selectin"
    )
    deletion_requests: Mapped[list[PlaidDeletionRequest]] = relationship(
        back_populates="connection", cascade="all, delete-orphan", lazy="selectin"
    )


class PlaidAccount(Base):
    __tablename__ = "plaid_accounts"
    __table_args__ = (
        UniqueConstraint("connection_id", "external_account_id", name="uq_plaid_accounts_connection_external"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    connection_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("plaid_connections.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    external_account_id: Mapped[str] = mapped_column(String(128), nullable=False)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    mask: Mapped[str | None] = mapped_column(String(16), nullable=True)
    account_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="USD")
    provenance: Mapped[str] = mapped_column(String(64), nullable=False, default=PROVENANCE_PLAID_READ_ONLY)
    source_label: Mapped[str] = mapped_column(String(128), nullable=False, default=SOURCE_LABEL_PLAID)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    connection: Mapped[PlaidConnection] = relationship(back_populates="accounts")
    holdings: Mapped[list[PlaidHolding]] = relationship(
        back_populates="account", cascade="all, delete-orphan", lazy="selectin"
    )


class PlaidHolding(Base):
    """Mirrored holdings with explicit read-only provenance — never linked to simulation."""

    __tablename__ = "plaid_holdings"
    __table_args__ = (
        UniqueConstraint("account_id", "external_security_id", name="uq_plaid_holdings_account_security"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("plaid_accounts.id", ondelete="CASCADE"), index=True, nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    external_security_id: Mapped[str] = mapped_column(String(128), nullable=False)
    symbol: Mapped[str | None] = mapped_column(String(32), nullable=True)
    name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False, default=Decimal("0"))
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="USD")
    provenance: Mapped[str] = mapped_column(String(64), nullable=False, default=PROVENANCE_PLAID_READ_ONLY)
    source_label: Mapped[str] = mapped_column(String(128), nullable=False, default=SOURCE_LABEL_PLAID)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    account: Mapped[PlaidAccount] = relationship(back_populates="holdings")


class PlaidDeletionRequest(Base):
    __tablename__ = "plaid_deletion_requests"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    connection_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("plaid_connections.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="requested")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    requested_by_subject: Mapped[str] = mapped_column(String(128), nullable=False)

    connection: Mapped[PlaidConnection] = relationship(back_populates="deletion_requests")
