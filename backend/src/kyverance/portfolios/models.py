"""Portfolio aggregate — owner-scoped private simulated workspaces."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from kyverance.db.session import Base
from kyverance.simulation.constants import (
    PORTFOLIO_PROVENANCE_SIMULATED,
    PORTFOLIO_STATUS_ACTIVE,
    PORTFOLIO_VISIBILITY_PRIVATE,
    VIRTUAL_CURRENCY_CODE,
)

if TYPE_CHECKING:
    from kyverance.simulation.models import SimWallet


class Portfolio(Base):
    """Owner-controlled simulated strategy workspace (private in SIM-01)."""

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
