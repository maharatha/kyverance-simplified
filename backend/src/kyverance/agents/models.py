"""Agent registry, immutable facts packets, and immutable proposals."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
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

from kyverance.agents.constants import (
    AGENT_STATUS_ACTIVE,
    FIXTURE_MODEL_NAME,
    FIXTURE_MODEL_PROVIDER,
    FIXTURE_MODEL_VERSION,
    FIXTURE_PROMPT_TEMPLATE_VERSION,
    PROPOSAL_STATUS_READY_FOR_REVIEW,
)
from kyverance.db.session import Base

# SQLite tests use JSON; Postgres migrations use JSONB via Alembic.
JsonType = JSON().with_variant(JSONB(), "postgresql")


class Agent(Base):
    """Owner-scoped private agent configuration for a portfolio."""

    __tablename__ = "agents"
    __table_args__ = (
        UniqueConstraint(
            "portfolio_id",
            "creation_idempotency_key",
            name="uq_agents_portfolio_creation_idem",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    portfolio_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("portfolios.id", ondelete="CASCADE"), index=True, nullable=False
    )
    owner_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    purpose: Mapped[str] = mapped_column(Text, nullable=False)
    capabilities_json: Mapped[list[Any]] = mapped_column(JsonType, nullable=False, default=list)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=AGENT_STATUS_ACTIVE)
    model_provider: Mapped[str] = mapped_column(String(64), nullable=False, default=FIXTURE_MODEL_PROVIDER)
    model_name: Mapped[str] = mapped_column(String(128), nullable=False, default=FIXTURE_MODEL_NAME)
    model_version: Mapped[str] = mapped_column(String(64), nullable=False, default=FIXTURE_MODEL_VERSION)
    prompt_template_version: Mapped[str] = mapped_column(
        String(64), nullable=False, default=FIXTURE_PROMPT_TEMPLATE_VERSION
    )
    budget_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=8_000)
    budget_usd_cents: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JsonType, nullable=False, default=dict)
    creation_idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    proposals: Mapped[list[AgentProposal]] = relationship(
        "AgentProposal",
        back_populates="agent",
        cascade="save-update, merge",
        lazy="selectin",
        order_by="AgentProposal.created_at.desc()",
    )


class AgentFactsPacket(Base):
    """Immutable authorized facts snapshot used as proposal grounding."""

    __tablename__ = "agent_facts_packets"
    __table_args__ = (
        UniqueConstraint(
            "portfolio_id",
            "creation_idempotency_key",
            name="uq_agent_facts_portfolio_creation_idem",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    portfolio_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("portfolios.id", ondelete="CASCADE"), index=True, nullable=False
    )
    owner_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    portfolio_version_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("portfolio_versions.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    data_as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    evidence_refs_json: Mapped[list[Any]] = mapped_column(JsonType, nullable=False, default=list)
    holdings_json: Mapped[list[Any]] = mapped_column(JsonType, nullable=False, default=list)
    cash_json: Mapped[dict[str, Any]] = mapped_column(JsonType, nullable=False, default=dict)
    risk_inputs_json: Mapped[dict[str, Any]] = mapped_column(JsonType, nullable=False, default=dict)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    creation_idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AgentProposal(Base):
    """Immutable agent proposal / forecast record. Never executes trades."""

    __tablename__ = "agent_proposals"
    __table_args__ = (
        UniqueConstraint(
            "agent_id",
            "creation_idempotency_key",
            name="uq_agent_proposals_agent_creation_idem",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), index=True, nullable=False
    )
    portfolio_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("portfolios.id", ondelete="CASCADE"), index=True, nullable=False
    )
    owner_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    facts_packet_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("agent_facts_packets.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )
    facts_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    proposal_type: Mapped[str] = mapped_column(String(64), nullable=False)
    horizon: Mapped[str] = mapped_column(String(64), nullable=False)
    assumptions_json: Mapped[list[Any]] = mapped_column(JsonType, nullable=False, default=list)
    actions_json: Mapped[list[Any]] = mapped_column(JsonType, nullable=False, default=list)
    draft_allocation_json: Mapped[dict[str, Any]] = mapped_column(JsonType, nullable=False, default=dict)
    evidence_refs_json: Mapped[list[Any]] = mapped_column(JsonType, nullable=False, default=list)
    confidence: Mapped[str] = mapped_column(String(32), nullable=False)
    limitations: Mapped[str] = mapped_column(Text, nullable=False)
    safety_decision: Mapped[str] = mapped_column(String(64), nullable=False)
    model_provider: Mapped[str] = mapped_column(String(64), nullable=False)
    model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    model_version: Mapped[str] = mapped_column(String(64), nullable=False)
    prompt_template_version: Mapped[str] = mapped_column(String(64), nullable=False)
    cost_usd_cents: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=PROPOSAL_STATUS_READY_FOR_REVIEW)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    data_as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    creation_idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    agent: Mapped[Agent] = relationship("Agent", back_populates="proposals")
