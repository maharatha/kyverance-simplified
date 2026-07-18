"""Canonical research ORM models mapped to MRKT-01 instruments."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

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
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from kyverance.db.session import Base
from kyverance.research.constants import (
    DEFAULT_MAX_ATTEMPTS,
    FRESHNESS_CURRENT,
    JOB_STATUS_PENDING,
    TIER_COLD,
)

JsonType = JSON().with_variant(JSONB(), "postgresql")


class ResearchSecurity(Base):
    """Canonical research identity linked to an internal instrument/listing."""

    __tablename__ = "research_securities"
    __table_args__ = (
        UniqueConstraint("instrument_id", "listing_id", name="uq_research_securities_instrument_listing"),
        UniqueConstraint("ticker", "exchange", name="uq_research_securities_ticker_exchange"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    instrument_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("instruments.id"), index=True, nullable=False
    )
    listing_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("instrument_listings.id"), index=True, nullable=False
    )
    ticker: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    exchange: Mapped[str] = mapped_column(String(16), index=True, nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    research_tier: Mapped[str] = mapped_column(String(16), nullable=False, default=TIER_COLD)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    last_viewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    tier_reason: Mapped[str | None] = mapped_column(String(128), nullable=True)
    tier_changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class SecurityResearchVersion(Base):
    """Immutable research version. Never mutate after publication."""

    __tablename__ = "security_research_versions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    security_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("research_securities.id"), index=True, nullable=False
    )
    ticker: Mapped[str] = mapped_column(String(32), nullable=False)
    exchange: Mapped[str] = mapped_column(String(16), nullable=False)
    market_date: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    prior_version_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("security_research_versions.id"), nullable=True
    )
    trigger_type: Mapped[str] = mapped_column(String(64), nullable=False)
    material_change_score: Mapped[Decimal | None] = mapped_column(Numeric(12, 6), nullable=True)
    changed_sections: Mapped[list[Any]] = mapped_column(JsonType, nullable=False, default=list)
    model_version: Mapped[str] = mapped_column(String(64), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(64), nullable=False)
    methodology_version: Mapped[str] = mapped_column(String(64), nullable=False)
    evidence_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    confidence_score: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)
    validation_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    publication_status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    freshness_status: Mapped[str] = mapped_column(String(32), nullable=False, default=FRESHNESS_CURRENT)
    artifact_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    change_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    executive_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    report_payload: Mapped[dict[str, Any] | None] = mapped_column(JsonType, nullable=True)
    evidence_refs: Mapped[list[Any]] = mapped_column(JsonType, nullable=False, default=list)
    source_data_timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_expected_refresh: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    valid_through: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SecurityResearchLatest(Base):
    """Latest-published pointer. Only validated published versions may be referenced."""

    __tablename__ = "security_research_latest"

    security_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("research_securities.id"), primary_key=True
    )
    version_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("security_research_versions.id"), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ResearchSection(Base):
    __tablename__ = "research_sections"
    __table_args__ = (
        UniqueConstraint("version_id", "section_key", name="uq_research_sections_version_key"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    version_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("security_research_versions.id"), index=True, nullable=False
    )
    security_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("research_securities.id"), index=True, nullable=False
    )
    section_key: Mapped[str] = mapped_column(String(64), nullable=False)
    evidence_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    reused_from_version_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    content: Mapped[dict[str, Any]] = mapped_column(JsonType, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class MaterialChangeAssessment(Base):
    __tablename__ = "material_change_assessments"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    security_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("research_securities.id"), index=True, nullable=False
    )
    market_date: Mapped[str] = mapped_column(String(16), nullable=False)
    score: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)
    band: Mapped[str] = mapped_column(String(32), nullable=False)
    decision: Mapped[str] = mapped_column(String(32), nullable=False)
    factors: Mapped[dict[str, Any]] = mapped_column(JsonType, nullable=False, default=dict)
    prior_version_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ResearchJob(Base):
    __tablename__ = "research_jobs"
    __table_args__ = (UniqueConstraint("idempotency_key", name="uq_research_jobs_idempotency"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    security_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("research_securities.id"), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=JOB_STATUS_PENDING, index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JsonType, nullable=False, default=dict)
    result: Mapped[dict[str, Any] | None] = mapped_column(JsonType, nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(256), nullable=False)
    correlation_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=DEFAULT_MAX_ATTEMPTS)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ResearchHealth(Base):
    __tablename__ = "research_health"

    component: Mapped[str] = mapped_column(String(64), primary_key=True)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ResearchSchedulerRun(Base):
    __tablename__ = "research_scheduler_runs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="running")
    session_day: Mapped[str | None] = mapped_column(String(16), nullable=True)
    result: Mapped[dict[str, Any] | None] = mapped_column(JsonType, nullable=True)
