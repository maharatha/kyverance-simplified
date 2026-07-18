"""Alembic revision: grounded canonical research foundation (RSRCH-01)."""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0009_research_foundation"
down_revision: Union[str, None] = "0008_market_data_foundation"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "research_securities",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("instrument_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("instruments.id"), nullable=False),
        sa.Column(
            "listing_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("instrument_listings.id"),
            nullable=False,
        ),
        sa.Column("ticker", sa.String(length=32), nullable=False),
        sa.Column("exchange", sa.String(length=16), nullable=False),
        sa.Column("display_name", sa.String(length=256), nullable=True),
        sa.Column("research_tier", sa.String(length=16), nullable=False, server_default="cold"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("last_viewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("tier_reason", sa.String(length=128), nullable=True),
        sa.Column("tier_changed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("instrument_id", "listing_id", name="uq_research_securities_instrument_listing"),
        sa.UniqueConstraint("ticker", "exchange", name="uq_research_securities_ticker_exchange"),
    )
    op.create_index("ix_research_securities_instrument_id", "research_securities", ["instrument_id"])
    op.create_index("ix_research_securities_listing_id", "research_securities", ["listing_id"])
    op.create_index("ix_research_securities_ticker", "research_securities", ["ticker"])
    op.create_index("ix_research_securities_exchange", "research_securities", ["exchange"])

    op.create_table(
        "security_research_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "security_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("research_securities.id"),
            nullable=False,
        ),
        sa.Column("ticker", sa.String(length=32), nullable=False),
        sa.Column("exchange", sa.String(length=16), nullable=False),
        sa.Column("market_date", sa.String(length=16), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "prior_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("security_research_versions.id"),
            nullable=True,
        ),
        sa.Column("trigger_type", sa.String(length=64), nullable=False),
        sa.Column("material_change_score", sa.Numeric(12, 6), nullable=True),
        sa.Column("changed_sections", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("model_version", sa.String(length=64), nullable=False),
        sa.Column("prompt_version", sa.String(length=64), nullable=False),
        sa.Column("methodology_version", sa.String(length=64), nullable=False),
        sa.Column("evidence_hash", sa.String(length=64), nullable=False),
        sa.Column("confidence_score", sa.Numeric(8, 4), nullable=True),
        sa.Column("validation_status", sa.String(length=32), nullable=False),
        sa.Column("publication_status", sa.String(length=32), nullable=False),
        sa.Column("freshness_status", sa.String(length=32), nullable=False, server_default="CURRENT"),
        sa.Column("artifact_key", sa.String(length=512), nullable=True),
        sa.Column("change_summary", sa.Text(), nullable=True),
        sa.Column("executive_summary", sa.Text(), nullable=True),
        sa.Column("report_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("evidence_refs", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("source_data_timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_expected_refresh", sa.DateTime(timezone=True), nullable=True),
        sa.Column("valid_through", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_security_research_versions_security_id", "security_research_versions", ["security_id"])
    op.create_index("ix_security_research_versions_market_date", "security_research_versions", ["market_date"])
    op.create_index("ix_security_research_versions_evidence_hash", "security_research_versions", ["evidence_hash"])
    op.create_index(
        "ix_security_research_versions_publication_status",
        "security_research_versions",
        ["publication_status"],
    )

    op.create_table(
        "security_research_latest",
        sa.Column(
            "security_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("research_securities.id"),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("security_research_versions.id"),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "research_sections",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("security_research_versions.id"),
            nullable=False,
        ),
        sa.Column(
            "security_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("research_securities.id"),
            nullable=False,
        ),
        sa.Column("section_key", sa.String(length=64), nullable=False),
        sa.Column("evidence_hash", sa.String(length=64), nullable=False),
        sa.Column("reused_from_version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("content", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("version_id", "section_key", name="uq_research_sections_version_key"),
    )
    op.create_index("ix_research_sections_version_id", "research_sections", ["version_id"])
    op.create_index("ix_research_sections_security_id", "research_sections", ["security_id"])

    op.create_table(
        "material_change_assessments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "security_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("research_securities.id"),
            nullable=False,
        ),
        sa.Column("market_date", sa.String(length=16), nullable=False),
        sa.Column("score", sa.Numeric(12, 6), nullable=False),
        sa.Column("band", sa.String(length=32), nullable=False),
        sa.Column("decision", sa.String(length=32), nullable=False),
        sa.Column("factors", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("prior_version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_material_change_assessments_security_id", "material_change_assessments", ["security_id"])

    op.create_table(
        "research_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("job_type", sa.String(length=64), nullable=False),
        sa.Column(
            "security_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("research_securities.id"),
            nullable=True,
        ),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("result", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("idempotency_key", sa.String(length=256), nullable=False),
        sa.Column("correlation_id", sa.String(length=64), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("idempotency_key", name="uq_research_jobs_idempotency"),
    )
    op.create_index("ix_research_jobs_job_type", "research_jobs", ["job_type"])
    op.create_index("ix_research_jobs_status", "research_jobs", ["status"])
    op.create_index("ix_research_jobs_security_id", "research_jobs", ["security_id"])
    op.create_index("ix_research_jobs_correlation_id", "research_jobs", ["correlation_id"])

    op.create_table(
        "research_health",
        sa.Column("component", sa.String(length=64), primary_key=True, nullable=False),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_message", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "research_scheduler_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="running"),
        sa.Column("session_day", sa.String(length=16), nullable=True),
        sa.Column("result", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("research_scheduler_runs")
    op.drop_table("research_health")
    op.drop_table("research_jobs")
    op.drop_table("material_change_assessments")
    op.drop_table("research_sections")
    op.drop_table("security_research_latest")
    op.drop_table("security_research_versions")
    op.drop_table("research_securities")
