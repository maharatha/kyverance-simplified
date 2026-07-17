"""Alembic revision: immutable portfolio versions, publish consent, independent forks."""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006_portfolio_versions_forks"
down_revision: Union[str, None] = "0005_simulated_orders"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("portfolios", sa.Column("thesis", sa.Text(), nullable=True))
    op.add_column("portfolios", sa.Column("agent_config_ref", sa.String(length=128), nullable=True))

    op.alter_column(
        "sim_position_lots",
        "execution_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
    )

    op.create_table(
        "portfolio_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("portfolio_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("owner_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("thesis", sa.Text(), nullable=True),
        sa.Column("agent_config_ref", sa.String(length=128), nullable=True),
        sa.Column("holdings_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("allocation_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("data_context_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("checksum", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("visibility", sa.String(length=32), nullable=False),
        sa.Column("provenance", sa.String(length=64), nullable=False),
        sa.Column("license", sa.String(length=64), nullable=True),
        sa.Column("disclosure", sa.Text(), nullable=True),
        sa.Column("consent_acknowledged", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("consent_text_version", sa.String(length=64), nullable=True),
        sa.Column("consent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("creation_idempotency_key", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["portfolio_id"], ["portfolios.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["published_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("portfolio_id", "version_number", name="uq_portfolio_version_number"),
        sa.UniqueConstraint(
            "portfolio_id",
            "creation_idempotency_key",
            name="uq_portfolio_version_creation_idem",
        ),
    )
    op.create_index("ix_portfolio_versions_portfolio_id", "portfolio_versions", ["portfolio_id"])
    op.create_index("ix_portfolio_versions_owner_user_id", "portfolio_versions", ["owner_user_id"])
    op.create_index(
        "ix_portfolio_versions_public",
        "portfolio_versions",
        ["status", "visibility", "license"],
    )

    op.create_table(
        "portfolio_forks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("forked_portfolio_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_portfolio_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("forked_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("license", sa.String(length=64), nullable=False),
        sa.Column("entitlement", sa.String(length=64), nullable=False),
        sa.Column("sync_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("mirror_trades", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("creation_idempotency_key", sa.String(length=128), nullable=True),
        sa.Column("forked_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["forked_portfolio_id"], ["portfolios.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_portfolio_id"], ["portfolios.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["source_version_id"], ["portfolio_versions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["forked_by_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("forked_portfolio_id", name="uq_portfolio_fork_target"),
        sa.UniqueConstraint(
            "forked_by_user_id",
            "creation_idempotency_key",
            name="uq_portfolio_fork_owner_creation_idem",
        ),
    )
    op.create_index("ix_portfolio_forks_source_portfolio_id", "portfolio_forks", ["source_portfolio_id"])
    op.create_index("ix_portfolio_forks_source_version_id", "portfolio_forks", ["source_version_id"])
    op.create_index("ix_portfolio_forks_forked_by_user_id", "portfolio_forks", ["forked_by_user_id"])


def downgrade() -> None:
    op.drop_table("portfolio_forks")
    op.drop_index("ix_portfolio_versions_public", table_name="portfolio_versions")
    op.drop_index("ix_portfolio_versions_owner_user_id", table_name="portfolio_versions")
    op.drop_index("ix_portfolio_versions_portfolio_id", table_name="portfolio_versions")
    op.drop_table("portfolio_versions")
    op.alter_column(
        "sim_position_lots",
        "execution_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )
    op.drop_column("portfolios", "agent_config_ref")
    op.drop_column("portfolios", "thesis")
