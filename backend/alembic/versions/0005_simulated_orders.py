"""Alembic revision: simulated order preview/confirm, positions, receipts."""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005_simulated_orders"
down_revision: Union[str, None] = "0004_portfolios_ledger"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "order_previews",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("portfolio_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("wallet_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("owner_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("side", sa.String(length=8), nullable=False),
        sa.Column("quantity", sa.Numeric(28, 10), nullable=False),
        sa.Column("notional", sa.Numeric(19, 4), nullable=False),
        sa.Column("quote_price", sa.Numeric(19, 4), nullable=False),
        sa.Column("execution_price", sa.Numeric(19, 4), nullable=False),
        sa.Column("slippage_bps", sa.Numeric(10, 4), nullable=False),
        sa.Column("fee", sa.Numeric(19, 4), nullable=False),
        sa.Column("quote_id", sa.String(length=128), nullable=False),
        sa.Column("quote_as_of", sa.DateTime(timezone=True), nullable=False),
        sa.Column("quote_received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("freshness_label", sa.String(length=32), nullable=False),
        sa.Column("data_mode", sa.String(length=32), nullable=False),
        sa.Column("execution_policy", sa.String(length=64), nullable=False),
        sa.Column("cash_after", sa.Numeric(19, 4), nullable=False),
        sa.Column("warnings_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("request_fingerprint", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["portfolio_id"], ["portfolios.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["wallet_id"], ["sim_wallets.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_order_previews_portfolio_id", "order_previews", ["portfolio_id"])
    op.create_index("ix_order_previews_wallet_id", "order_previews", ["wallet_id"])
    op.create_index("ix_order_previews_owner_user_id", "order_previews", ["owner_user_id"])

    op.create_table(
        "sim_orders",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("portfolio_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("wallet_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("owner_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("preview_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("side", sa.String(length=8), nullable=False),
        sa.Column("quantity", sa.Numeric(28, 10), nullable=False),
        sa.Column("notional", sa.Numeric(19, 4), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("request_fingerprint", sa.String(length=128), nullable=False),
        sa.Column("quote_id", sa.String(length=128), nullable=False),
        sa.Column("reject_reason", sa.String(length=256), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["portfolio_id"], ["portfolios.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["wallet_id"], ["sim_wallets.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["preview_id"], ["order_previews.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("preview_id"),
        sa.UniqueConstraint("owner_user_id", "idempotency_key", name="uq_sim_order_owner_idem"),
    )
    op.create_index("ix_sim_orders_portfolio_id", "sim_orders", ["portfolio_id"])
    op.create_index("ix_sim_orders_wallet_id", "sim_orders", ["wallet_id"])
    op.create_index("ix_sim_orders_owner_user_id", "sim_orders", ["owner_user_id"])
    op.create_index("ix_sim_orders_symbol", "sim_orders", ["symbol"])

    op.create_table(
        "sim_executions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("side", sa.String(length=8), nullable=False),
        sa.Column("quantity", sa.Numeric(28, 10), nullable=False),
        sa.Column("price", sa.Numeric(19, 4), nullable=False),
        sa.Column("notional", sa.Numeric(19, 4), nullable=False),
        sa.Column("fee", sa.Numeric(19, 4), nullable=False),
        sa.Column("slippage_bps", sa.Numeric(10, 4), nullable=False),
        sa.Column("quote_id", sa.String(length=128), nullable=False),
        sa.Column("quote_as_of", sa.DateTime(timezone=True), nullable=False),
        sa.Column("quote_received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("freshness_label", sa.String(length=32), nullable=False),
        sa.Column("data_mode", sa.String(length=32), nullable=False),
        sa.Column("execution_policy", sa.String(length=64), nullable=False),
        sa.Column("simulated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["order_id"], ["sim_orders.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("order_id"),
    )

    op.create_table(
        "sim_positions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("portfolio_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("quantity", sa.Numeric(28, 10), nullable=False),
        sa.Column("avg_cost", sa.Numeric(19, 4), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["portfolio_id"], ["portfolios.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("portfolio_id", "symbol", name="uq_sim_pos_symbol"),
    )
    op.create_index("ix_sim_positions_portfolio_id", "sim_positions", ["portfolio_id"])

    op.create_table(
        "sim_position_lots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("portfolio_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("quantity_remaining", sa.Numeric(28, 10), nullable=False),
        sa.Column("unit_cost", sa.Numeric(19, 4), nullable=False),
        sa.Column("opened_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("execution_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["portfolio_id"], ["portfolios.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["execution_id"], ["sim_executions.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_sim_position_lots_portfolio_id", "sim_position_lots", ["portfolio_id"])
    op.create_index("ix_sim_position_lots_symbol", "sim_position_lots", ["symbol"])

    op.create_table(
        "order_receipts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("portfolio_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("owner_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("payload_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["order_id"], ["sim_orders.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["portfolio_id"], ["portfolios.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("order_id"),
    )
    op.create_index("ix_order_receipts_portfolio_id", "order_receipts", ["portfolio_id"])
    op.create_index("ix_order_receipts_owner_user_id", "order_receipts", ["owner_user_id"])

    op.create_table(
        "reconciliation_incidents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("portfolio_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("owner_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("kind", sa.String(length=64), nullable=False),
        sa.Column("detail", sa.Text(), nullable=False),
        sa.Column("snapshot_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["portfolio_id"], ["portfolios.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_reconciliation_incidents_portfolio_id", "reconciliation_incidents", ["portfolio_id"])
    op.create_index("ix_reconciliation_incidents_owner_user_id", "reconciliation_incidents", ["owner_user_id"])

    op.add_column(
        "wallet_ledger_entries",
        sa.Column("related_order_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index(
        "ix_wallet_ledger_entries_related_order_id",
        "wallet_ledger_entries",
        ["related_order_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_wallet_ledger_entries_related_order_id", table_name="wallet_ledger_entries")
    op.drop_column("wallet_ledger_entries", "related_order_id")
    op.drop_index("ix_reconciliation_incidents_owner_user_id", table_name="reconciliation_incidents")
    op.drop_index("ix_reconciliation_incidents_portfolio_id", table_name="reconciliation_incidents")
    op.drop_table("reconciliation_incidents")
    op.drop_index("ix_order_receipts_owner_user_id", table_name="order_receipts")
    op.drop_index("ix_order_receipts_portfolio_id", table_name="order_receipts")
    op.drop_table("order_receipts")
    op.drop_index("ix_sim_position_lots_symbol", table_name="sim_position_lots")
    op.drop_index("ix_sim_position_lots_portfolio_id", table_name="sim_position_lots")
    op.drop_table("sim_position_lots")
    op.drop_index("ix_sim_positions_portfolio_id", table_name="sim_positions")
    op.drop_table("sim_positions")
    op.drop_table("sim_executions")
    op.drop_index("ix_sim_orders_symbol", table_name="sim_orders")
    op.drop_index("ix_sim_orders_owner_user_id", table_name="sim_orders")
    op.drop_index("ix_sim_orders_wallet_id", table_name="sim_orders")
    op.drop_index("ix_sim_orders_portfolio_id", table_name="sim_orders")
    op.drop_table("sim_orders")
    op.drop_index("ix_order_previews_owner_user_id", table_name="order_previews")
    op.drop_index("ix_order_previews_wallet_id", table_name="order_previews")
    op.drop_index("ix_order_previews_portfolio_id", table_name="order_previews")
    op.drop_table("order_previews")
