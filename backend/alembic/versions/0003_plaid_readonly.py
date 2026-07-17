"""Plaid read-only connection tables."""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_plaid_readonly"
down_revision: Union[str, None] = "0002_identity_rbac"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "plaid_connections",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("item_id", sa.String(length=128), nullable=False),
        sa.Column("access_token_ciphertext", sa.Text(), nullable=True),
        sa.Column("token_vault_ref", sa.String(length=256), nullable=True),
        sa.Column("encryption_kid", sa.String(length=64), nullable=True),
        sa.Column("provider_key", sa.String(length=64), nullable=False),
        sa.Column("institution_name", sa.String(length=256), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("consent_recorded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("disconnected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deletion_requested_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_plaid_connections_user_id", "plaid_connections", ["user_id"])
    op.create_index("ix_plaid_connections_item_id", "plaid_connections", ["item_id"])

    op.create_table(
        "plaid_accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("connection_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("external_account_id", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=256), nullable=False),
        sa.Column("mask", sa.String(length=16), nullable=True),
        sa.Column("account_type", sa.String(length=64), nullable=True),
        sa.Column("currency", sa.String(length=8), nullable=False),
        sa.Column("provenance", sa.String(length=64), nullable=False),
        sa.Column("source_label", sa.String(length=128), nullable=False),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["connection_id"], ["plaid_connections.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("connection_id", "external_account_id", name="uq_plaid_accounts_connection_external"),
    )
    op.create_index("ix_plaid_accounts_connection_id", "plaid_accounts", ["connection_id"])
    op.create_index("ix_plaid_accounts_user_id", "plaid_accounts", ["user_id"])

    op.create_table(
        "plaid_holdings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("external_security_id", sa.String(length=128), nullable=False),
        sa.Column("symbol", sa.String(length=32), nullable=True),
        sa.Column("name", sa.String(length=256), nullable=True),
        sa.Column("quantity", sa.Numeric(24, 8), nullable=False),
        sa.Column("currency", sa.String(length=8), nullable=False),
        sa.Column("provenance", sa.String(length=64), nullable=False),
        sa.Column("source_label", sa.String(length=128), nullable=False),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["plaid_accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("account_id", "external_security_id", name="uq_plaid_holdings_account_security"),
    )
    op.create_index("ix_plaid_holdings_account_id", "plaid_holdings", ["account_id"])
    op.create_index("ix_plaid_holdings_user_id", "plaid_holdings", ["user_id"])

    op.create_table(
        "plaid_deletion_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("connection_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("requested_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("requested_by_subject", sa.String(length=128), nullable=False),
        sa.ForeignKeyConstraint(["connection_id"], ["plaid_connections.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_plaid_deletion_requests_connection_id", "plaid_deletion_requests", ["connection_id"])
    op.create_index("ix_plaid_deletion_requests_user_id", "plaid_deletion_requests", ["user_id"])


def downgrade() -> None:
    op.drop_table("plaid_deletion_requests")
    op.drop_table("plaid_holdings")
    op.drop_table("plaid_accounts")
    op.drop_table("plaid_connections")
