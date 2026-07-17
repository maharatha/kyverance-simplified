"""Alembic revision: market-data warehouse and durable job foundation (MRKT-01)."""

from __future__ import annotations

from typing import Sequence, Union
from uuid import uuid4

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0008_market_data_foundation"
down_revision: Union[str, None] = "0007_agent_foundation"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "data_providers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("provider_type", sa.String(length=32), nullable=False, server_default="eod"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("configuration_reference", sa.String(length=256), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("code", name="uq_data_providers_code"),
    )
    op.create_index("ix_data_providers_code", "data_providers", ["code"])

    op.create_table(
        "market_exchanges",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("mic_code", sa.String(length=16), nullable=False),
        sa.Column("canonical_code", sa.String(length=16), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("country_code", sa.String(length=2), nullable=False, server_default="US"),
        sa.Column("currency_code", sa.String(length=3), nullable=False, server_default="USD"),
        sa.Column("timezone", sa.String(length=64), nullable=False, server_default="America/New_York"),
        sa.Column("regular_open_time", sa.String(length=8), nullable=False, server_default="09:30"),
        sa.Column("regular_close_time", sa.String(length=8), nullable=False, server_default="16:00"),
        sa.Column(
            "default_data_availability_delay_minutes",
            sa.Integer(),
            nullable=False,
            server_default="90",
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("canonical_code", name="uq_market_exchanges_canonical"),
        sa.UniqueConstraint("mic_code", name="uq_market_exchanges_mic"),
    )
    op.create_index("ix_market_exchanges_mic_code", "market_exchanges", ["mic_code"])
    op.create_index("ix_market_exchanges_canonical_code", "market_exchanges", ["canonical_code"])

    op.create_table(
        "exchange_trading_days",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("exchange_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("trading_date", sa.Date(), nullable=False),
        sa.Column("is_trading_day", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("open_time", sa.String(length=8), nullable=True),
        sa.Column("close_time", sa.String(length=8), nullable=True),
        sa.Column("is_early_close", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("source", sa.String(length=32), nullable=False, server_default="weekday_seed"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["exchange_id"], ["market_exchanges.id"]),
        sa.UniqueConstraint("exchange_id", "trading_date", name="uq_exchange_trading_day"),
    )
    op.create_index("ix_exchange_trading_days_exchange_id", "exchange_trading_days", ["exchange_id"])
    op.create_index("ix_exchange_trading_days_trading_date", "exchange_trading_days", ["trading_date"])

    op.create_table(
        "instruments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("instrument_type", sa.String(length=32), nullable=False, server_default="equity"),
        sa.Column("canonical_name", sa.String(length=256), nullable=False),
        sa.Column("primary_exchange_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("primary_currency_code", sa.String(length=3), nullable=False, server_default="USD"),
        sa.Column("isin", sa.String(length=16), nullable=True),
        sa.Column("cusip", sa.String(length=16), nullable=True),
        sa.Column("figi", sa.String(length=16), nullable=True),
        sa.Column("listing_date", sa.Date(), nullable=True),
        sa.Column("delisting_date", sa.Date(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["primary_exchange_id"], ["market_exchanges.id"]),
    )
    op.create_index("ix_instruments_primary_exchange_id", "instruments", ["primary_exchange_id"])

    op.create_table(
        "instrument_listings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("instrument_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("exchange_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ticker", sa.String(length=32), nullable=False),
        sa.Column("currency_code", sa.String(length=3), nullable=False, server_default="USD"),
        sa.Column("valid_from", sa.Date(), nullable=True),
        sa.Column("valid_to", sa.Date(), nullable=True),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["instrument_id"], ["instruments.id"]),
        sa.ForeignKeyConstraint(["exchange_id"], ["market_exchanges.id"]),
    )
    op.create_index("ix_instrument_listings_instrument_id", "instrument_listings", ["instrument_id"])
    op.create_index("ix_instrument_listings_exchange_id", "instrument_listings", ["exchange_id"])
    op.create_index("ix_instrument_listings_ticker", "instrument_listings", ["ticker"])
    op.create_index(
        "ix_instrument_listings_exchange_ticker",
        "instrument_listings",
        ["exchange_id", "ticker"],
    )

    op.create_table(
        "provider_instrument_mappings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("provider_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("instrument_listing_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider_symbol", sa.String(length=64), nullable=False),
        sa.Column("provider_exchange_code", sa.String(length=32), nullable=False, server_default="US"),
        sa.Column("valid_from", sa.Date(), nullable=True),
        sa.Column("valid_to", sa.Date(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("provider_metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["provider_id"], ["data_providers.id"]),
        sa.ForeignKeyConstraint(["instrument_listing_id"], ["instrument_listings.id"]),
        sa.UniqueConstraint(
            "provider_id",
            "provider_symbol",
            "provider_exchange_code",
            "valid_from",
            name="uq_provider_instrument_mapping",
        ),
    )
    op.create_index(
        "ix_provider_instrument_mappings_provider_id",
        "provider_instrument_mappings",
        ["provider_id"],
    )
    op.create_index(
        "ix_provider_instrument_mappings_instrument_listing_id",
        "provider_instrument_mappings",
        ["instrument_listing_id"],
    )
    op.create_index(
        "ix_provider_instrument_mappings_provider_symbol",
        "provider_instrument_mappings",
        ["provider_symbol"],
    )

    op.create_table(
        "daily_prices",
        sa.Column("instrument_listing_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("trading_date", sa.Date(), nullable=False),
        sa.Column("open", sa.Numeric(20, 8), nullable=False),
        sa.Column("high", sa.Numeric(20, 8), nullable=False),
        sa.Column("low", sa.Numeric(20, 8), nullable=False),
        sa.Column("close", sa.Numeric(20, 8), nullable=False),
        sa.Column("adjusted_close", sa.Numeric(20, 8), nullable=True),
        sa.Column("volume", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("currency_code", sa.String(length=3), nullable=False, server_default="USD"),
        sa.Column("provider_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("data_status", sa.String(length=16), nullable=False, server_default="FINAL"),
        sa.Column("data_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["instrument_listing_id"], ["instrument_listings.id"]),
        sa.ForeignKeyConstraint(["provider_id"], ["data_providers.id"]),
        sa.PrimaryKeyConstraint("instrument_listing_id", "trading_date"),
        sa.UniqueConstraint(
            "instrument_listing_id",
            "trading_date",
            name="uq_daily_prices_listing_date",
        ),
    )
    op.create_index("ix_daily_prices_trading_date", "daily_prices", ["trading_date"])
    op.create_index(
        "ix_daily_prices_listing_date_desc",
        "daily_prices",
        ["instrument_listing_id", "trading_date"],
    )
    op.create_index("ix_daily_prices_provider_id", "daily_prices", ["provider_id"])

    op.create_table(
        "latest_daily_prices",
        sa.Column("instrument_listing_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("trading_date", sa.Date(), nullable=False),
        sa.Column("open", sa.Numeric(20, 8), nullable=False),
        sa.Column("high", sa.Numeric(20, 8), nullable=False),
        sa.Column("low", sa.Numeric(20, 8), nullable=False),
        sa.Column("close", sa.Numeric(20, 8), nullable=False),
        sa.Column("adjusted_close", sa.Numeric(20, 8), nullable=True),
        sa.Column("volume", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("currency_code", sa.String(length=3), nullable=False, server_default="USD"),
        sa.Column("provider_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("data_status", sa.String(length=16), nullable=False, server_default="FINAL"),
        sa.Column("data_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["instrument_listing_id"], ["instrument_listings.id"]),
    )
    op.create_index("ix_latest_daily_prices_trading_date", "latest_daily_prices", ["trading_date"])

    op.create_table(
        "ingestion_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("provider_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("exchange_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("job_type", sa.String(length=64), nullable=False),
        sa.Column("trading_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="QUEUED"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("records_received", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("records_normalized", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("records_inserted", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("records_updated", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("records_rejected", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("raw_object_uri", sa.Text(), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["provider_id"], ["data_providers.id"]),
        sa.ForeignKeyConstraint(["exchange_id"], ["market_exchanges.id"]),
        sa.UniqueConstraint(
            "provider_id",
            "exchange_id",
            "job_type",
            "trading_date",
            name="uq_ingestion_run_logical",
        ),
    )
    op.create_index("ix_ingestion_runs_provider_id", "ingestion_runs", ["provider_id"])
    op.create_index("ix_ingestion_runs_exchange_id", "ingestion_runs", ["exchange_id"])
    op.create_index("ix_ingestion_runs_job_type", "ingestion_runs", ["job_type"])
    op.create_index("ix_ingestion_runs_trading_date", "ingestion_runs", ["trading_date"])
    op.create_index("ix_ingestion_runs_status", "ingestion_runs", ["status"])

    op.create_table(
        "ingestion_errors",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("ingestion_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider_record_identifier", sa.String(length=128), nullable=True),
        sa.Column("error_type", sa.String(length=64), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=False),
        sa.Column("raw_record_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["ingestion_run_id"], ["ingestion_runs.id"]),
    )
    op.create_index("ix_ingestion_errors_ingestion_run_id", "ingestion_errors", ["ingestion_run_id"])

    op.create_table(
        "market_data_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("job_type", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("idempotency_key", sa.String(length=256), nullable=False),
        sa.Column("correlation_id", sa.String(length=64), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("result", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("idempotency_key", name="uq_market_data_jobs_idempotency"),
    )
    op.create_index("ix_market_data_jobs_job_type", "market_data_jobs", ["job_type"])
    op.create_index("ix_market_data_jobs_status", "market_data_jobs", ["status"])

    op.create_table(
        "market_data_health",
        sa.Column("component", sa.String(length=64), primary_key=True, nullable=False),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_message", sa.Text(), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # Seed providers + US exchanges (no secrets).
    fake_id = str(uuid4())
    live_id = str(uuid4())
    xnys_id = str(uuid4())
    xnas_id = str(uuid4())
    op.execute(
        f"""
        INSERT INTO data_providers (id, code, name, provider_type, is_active)
        VALUES
          ('{fake_id}', 'fake', 'Deterministic fake provider', 'eod', true),
          ('{live_id}', 'live', 'Live provider (disabled until configured)', 'eod', false)
        """
    )
    op.execute(
        f"""
        INSERT INTO market_exchanges (
          id, mic_code, canonical_code, name, country_code, currency_code, timezone,
          regular_open_time, regular_close_time, default_data_availability_delay_minutes, is_active
        ) VALUES
          ('{xnys_id}', 'XNYS', 'XNYS', 'New York Stock Exchange', 'US', 'USD',
           'America/New_York', '09:30', '16:00', 90, true),
          ('{xnas_id}', 'XNAS', 'XNAS', 'NASDAQ', 'US', 'USD',
           'America/New_York', '09:30', '16:00', 90, true)
        """
    )


def downgrade() -> None:
    op.drop_table("market_data_health")
    op.drop_table("market_data_jobs")
    op.drop_table("ingestion_errors")
    op.drop_table("ingestion_runs")
    op.drop_table("latest_daily_prices")
    op.drop_table("daily_prices")
    op.drop_table("provider_instrument_mappings")
    op.drop_table("instrument_listings")
    op.drop_table("instruments")
    op.drop_table("exchange_trading_days")
    op.drop_table("market_exchanges")
    op.drop_table("data_providers")
