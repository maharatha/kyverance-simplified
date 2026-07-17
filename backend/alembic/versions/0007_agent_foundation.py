"""Alembic revision: agent registry, facts packets, and proposals (AGENT-01)."""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007_agent_foundation"
down_revision: Union[str, None] = "0006_portfolio_versions_forks"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "agents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("portfolio_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("owner_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("purpose", sa.Text(), nullable=False),
        sa.Column("capabilities_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("model_provider", sa.String(length=64), nullable=False),
        sa.Column("model_name", sa.String(length=128), nullable=False),
        sa.Column("model_version", sa.String(length=64), nullable=False),
        sa.Column("prompt_template_version", sa.String(length=64), nullable=False),
        sa.Column("budget_tokens", sa.Integer(), nullable=False),
        sa.Column("budget_usd_cents", sa.Integer(), nullable=False),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("creation_idempotency_key", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["portfolio_id"], ["portfolios.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "portfolio_id",
            "creation_idempotency_key",
            name="uq_agents_portfolio_creation_idem",
        ),
    )
    op.create_index("ix_agents_portfolio_id", "agents", ["portfolio_id"])
    op.create_index("ix_agents_owner_user_id", "agents", ["owner_user_id"])

    op.create_table(
        "agent_facts_packets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("portfolio_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("owner_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("portfolio_version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("data_as_of", sa.DateTime(timezone=True), nullable=False),
        sa.Column("evidence_refs_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("holdings_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("cash_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("risk_inputs_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("checksum", sa.String(length=64), nullable=False),
        sa.Column("creation_idempotency_key", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["portfolio_id"], ["portfolios.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["portfolio_version_id"], ["portfolio_versions.id"], ondelete="SET NULL"),
        sa.UniqueConstraint(
            "portfolio_id",
            "creation_idempotency_key",
            name="uq_agent_facts_portfolio_creation_idem",
        ),
    )
    op.create_index("ix_agent_facts_packets_portfolio_id", "agent_facts_packets", ["portfolio_id"])
    op.create_index("ix_agent_facts_packets_owner_user_id", "agent_facts_packets", ["owner_user_id"])
    op.create_index(
        "ix_agent_facts_packets_portfolio_version_id",
        "agent_facts_packets",
        ["portfolio_version_id"],
    )

    op.create_table(
        "agent_proposals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("portfolio_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("owner_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("facts_packet_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("facts_checksum", sa.String(length=64), nullable=False),
        sa.Column("proposal_type", sa.String(length=64), nullable=False),
        sa.Column("horizon", sa.String(length=64), nullable=False),
        sa.Column("assumptions_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("actions_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("draft_allocation_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("evidence_refs_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("confidence", sa.String(length=32), nullable=False),
        sa.Column("limitations", sa.Text(), nullable=False),
        sa.Column("safety_decision", sa.String(length=64), nullable=False),
        sa.Column("model_provider", sa.String(length=64), nullable=False),
        sa.Column("model_name", sa.String(length=128), nullable=False),
        sa.Column("model_version", sa.String(length=64), nullable=False),
        sa.Column("prompt_template_version", sa.String(length=64), nullable=False),
        sa.Column("cost_usd_cents", sa.Integer(), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("data_as_of", sa.DateTime(timezone=True), nullable=False),
        sa.Column("creation_idempotency_key", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["portfolio_id"], ["portfolios.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["facts_packet_id"], ["agent_facts_packets.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint(
            "agent_id",
            "creation_idempotency_key",
            name="uq_agent_proposals_agent_creation_idem",
        ),
    )
    op.create_index("ix_agent_proposals_agent_id", "agent_proposals", ["agent_id"])
    op.create_index("ix_agent_proposals_portfolio_id", "agent_proposals", ["portfolio_id"])
    op.create_index("ix_agent_proposals_owner_user_id", "agent_proposals", ["owner_user_id"])
    op.create_index("ix_agent_proposals_facts_packet_id", "agent_proposals", ["facts_packet_id"])


def downgrade() -> None:
    op.drop_index("ix_agent_proposals_facts_packet_id", table_name="agent_proposals")
    op.drop_index("ix_agent_proposals_owner_user_id", table_name="agent_proposals")
    op.drop_index("ix_agent_proposals_portfolio_id", table_name="agent_proposals")
    op.drop_index("ix_agent_proposals_agent_id", table_name="agent_proposals")
    op.drop_table("agent_proposals")

    op.drop_index("ix_agent_facts_packets_portfolio_version_id", table_name="agent_facts_packets")
    op.drop_index("ix_agent_facts_packets_owner_user_id", table_name="agent_facts_packets")
    op.drop_index("ix_agent_facts_packets_portfolio_id", table_name="agent_facts_packets")
    op.drop_table("agent_facts_packets")

    op.drop_index("ix_agents_owner_user_id", table_name="agents")
    op.drop_index("ix_agents_portfolio_id", table_name="agents")
    op.drop_table("agents")
