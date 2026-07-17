"""Portfolio aggregate — owner-scoped simulated workspaces, versions, and forks."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
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
from kyverance.portfolios.constants import (
    VERSION_STATUS_DRAFT,
    VERSION_VISIBILITY_PRIVATE,
)
from kyverance.simulation.constants import (
    PORTFOLIO_PROVENANCE_SIMULATED,
    PORTFOLIO_STATUS_ACTIVE,
    PORTFOLIO_VISIBILITY_PRIVATE,
    VIRTUAL_CURRENCY_CODE,
)

if TYPE_CHECKING:
    from kyverance.simulation.models import SimWallet

# SQLite tests use JSON; Postgres migrations use JSONB via Alembic.
JsonType = JSON().with_variant(JSONB(), "postgresql")


class Portfolio(Base):
    """Owner-controlled simulated strategy workspace (private by default)."""

    __tablename__ = "portfolios"
    __table_args__ = (
        UniqueConstraint(
            "owner_user_id",
            "creation_idempotency_key",
            name="uq_portfolios_owner_creation_idem",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    thesis: Mapped[str | None] = mapped_column(Text, nullable=True)
    agent_config_ref: Mapped[str | None] = mapped_column(String(128), nullable=True)
    visibility: Mapped[str] = mapped_column(String(32), nullable=False, default=PORTFOLIO_VISIBILITY_PRIVATE)
    provenance: Mapped[str] = mapped_column(String(64), nullable=False, default=PORTFOLIO_PROVENANCE_SIMULATED)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=PORTFOLIO_STATUS_ACTIVE)
    currency_code: Mapped[str] = mapped_column(String(8), nullable=False, default=VIRTUAL_CURRENCY_CODE)
    # Client-supplied key for idempotent creation (unique per owner when present).
    creation_idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    wallet: Mapped[SimWallet | None] = relationship(
        "SimWallet",
        back_populates="portfolio",
        uselist=False,
        cascade="save-update, merge",
        lazy="selectin",
    )
    versions: Mapped[list[PortfolioVersion]] = relationship(
        "PortfolioVersion",
        back_populates="portfolio",
        cascade="save-update, merge",
        lazy="selectin",
        order_by="PortfolioVersion.version_number",
    )
    fork_lineage: Mapped[PortfolioFork | None] = relationship(
        "PortfolioFork",
        back_populates="forked_portfolio",
        uselist=False,
        cascade="save-update, merge",
        lazy="selectin",
        foreign_keys="PortfolioFork.forked_portfolio_id",
    )


class PortfolioVersion(Base):
    """Immutable snapshot of portfolio metadata, thesis, holdings, and data context."""

    __tablename__ = "portfolio_versions"
    __table_args__ = (
        UniqueConstraint("portfolio_id", "version_number", name="uq_portfolio_version_number"),
        UniqueConstraint(
            "portfolio_id",
            "creation_idempotency_key",
            name="uq_portfolio_version_creation_idem",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    portfolio_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("portfolios.id", ondelete="CASCADE"), index=True, nullable=False
    )
    owner_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    thesis: Mapped[str | None] = mapped_column(Text, nullable=True)
    agent_config_ref: Mapped[str | None] = mapped_column(String(128), nullable=True)
    holdings_json: Mapped[list[Any]] = mapped_column(JsonType, nullable=False, default=list)
    allocation_json: Mapped[dict[str, Any]] = mapped_column(JsonType, nullable=False, default=dict)
    data_context_json: Mapped[dict[str, Any]] = mapped_column(JsonType, nullable=False, default=dict)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=VERSION_STATUS_DRAFT)
    visibility: Mapped[str] = mapped_column(String(32), nullable=False, default=VERSION_VISIBILITY_PRIVATE)
    provenance: Mapped[str] = mapped_column(String(64), nullable=False, default=PORTFOLIO_PROVENANCE_SIMULATED)
    license: Mapped[str | None] = mapped_column(String(64), nullable=True)
    disclosure: Mapped[str | None] = mapped_column(Text, nullable=True)
    consent_acknowledged: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    consent_text_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    consent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    published_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    creation_idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    portfolio: Mapped[Portfolio] = relationship("Portfolio", back_populates="versions")


class PortfolioFork(Base):
    """Durable source lineage for an independent simulated fork. Append-only."""

    __tablename__ = "portfolio_forks"
    __table_args__ = (
        UniqueConstraint("forked_portfolio_id", name="uq_portfolio_fork_target"),
        UniqueConstraint(
            "forked_by_user_id",
            "creation_idempotency_key",
            name="uq_portfolio_fork_owner_creation_idem",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    forked_portfolio_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("portfolios.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_portfolio_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("portfolios.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    source_version_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("portfolio_versions.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )
    forked_by_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    license: Mapped[str] = mapped_column(String(64), nullable=False)
    entitlement: Mapped[str] = mapped_column(String(64), nullable=False)
    sync_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    mirror_trades: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    creation_idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    forked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    forked_portfolio: Mapped[Portfolio] = relationship(
        "Portfolio",
        back_populates="fork_lineage",
        foreign_keys=[forked_portfolio_id],
    )
