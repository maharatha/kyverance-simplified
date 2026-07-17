"""Canonical market-data warehouse ORM models."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
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
from kyverance.market_data.constants import (
    DATA_STATUS_FINAL,
    DEFAULT_MAX_ATTEMPTS,
    INGEST_STATUS_QUEUED,
    JOB_STATUS_PENDING,
)

JsonType = JSON().with_variant(JSONB(), "postgresql")


class DataProvider(Base):
    __tablename__ = "data_providers"
    __table_args__ = (UniqueConstraint("code", name="uq_data_providers_code"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(32), index=True)
    name: Mapped[str] = mapped_column(String(128))
    provider_type: Mapped[str] = mapped_column(String(32), default="eod")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    configuration_reference: Mapped[str | None] = mapped_column(String(256), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class MarketExchange(Base):
    __tablename__ = "market_exchanges"
    __table_args__ = (
        UniqueConstraint("canonical_code", name="uq_market_exchanges_canonical"),
        UniqueConstraint("mic_code", name="uq_market_exchanges_mic"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mic_code: Mapped[str] = mapped_column(String(16), index=True)
    canonical_code: Mapped[str] = mapped_column(String(16), index=True)
    name: Mapped[str] = mapped_column(String(128))
    country_code: Mapped[str] = mapped_column(String(2), default="US")
    currency_code: Mapped[str] = mapped_column(String(3), default="USD")
    timezone: Mapped[str] = mapped_column(String(64), default="America/New_York")
    regular_open_time: Mapped[str] = mapped_column(String(8), default="09:30")
    regular_close_time: Mapped[str] = mapped_column(String(8), default="16:00")
    default_data_availability_delay_minutes: Mapped[int] = mapped_column(Integer, default=90)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ExchangeTradingDay(Base):
    __tablename__ = "exchange_trading_days"
    __table_args__ = (UniqueConstraint("exchange_id", "trading_date", name="uq_exchange_trading_day"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    exchange_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("market_exchanges.id"), index=True
    )
    trading_date: Mapped[date] = mapped_column(Date, index=True)
    is_trading_day: Mapped[bool] = mapped_column(Boolean, default=True)
    open_time: Mapped[str | None] = mapped_column(String(8), nullable=True)
    close_time: Mapped[str | None] = mapped_column(String(8), nullable=True)
    is_early_close: Mapped[bool] = mapped_column(Boolean, default=False)
    source: Mapped[str] = mapped_column(String(32), default="weekday_seed")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Instrument(Base):
    __tablename__ = "instruments"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    instrument_type: Mapped[str] = mapped_column(String(32), default="equity")
    canonical_name: Mapped[str] = mapped_column(String(256))
    primary_exchange_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("market_exchanges.id"), nullable=True, index=True
    )
    primary_currency_code: Mapped[str] = mapped_column(String(3), default="USD")
    isin: Mapped[str | None] = mapped_column(String(16), nullable=True)
    cusip: Mapped[str | None] = mapped_column(String(16), nullable=True)
    figi: Mapped[str | None] = mapped_column(String(16), nullable=True)
    listing_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    delisting_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class InstrumentListing(Base):
    __tablename__ = "instrument_listings"
    __table_args__ = (Index("ix_instrument_listings_exchange_ticker", "exchange_id", "ticker"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    instrument_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("instruments.id"), index=True
    )
    exchange_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("market_exchanges.id"), index=True
    )
    ticker: Mapped[str] = mapped_column(String(32), index=True)
    currency_code: Mapped[str] = mapped_column(String(3), default="USD")
    valid_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    valid_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ProviderInstrumentMapping(Base):
    __tablename__ = "provider_instrument_mappings"
    __table_args__ = (
        UniqueConstraint(
            "provider_id",
            "provider_symbol",
            "provider_exchange_code",
            "valid_from",
            name="uq_provider_instrument_mapping",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("data_providers.id"), index=True
    )
    instrument_listing_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("instrument_listings.id"), index=True
    )
    provider_symbol: Mapped[str] = mapped_column(String(64), index=True)
    provider_exchange_code: Mapped[str] = mapped_column(String(32), default="US")
    valid_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    valid_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    provider_metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JsonType, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class DailyPrice(Base):
    """Operational EOD bars. Unpartitioned for local/CI; port for later partitions."""

    __tablename__ = "daily_prices"
    __table_args__ = (
        UniqueConstraint("instrument_listing_id", "trading_date", name="uq_daily_prices_listing_date"),
        Index("ix_daily_prices_listing_date_desc", "instrument_listing_id", "trading_date"),
        Index("ix_daily_prices_trading_date", "trading_date"),
    )

    instrument_listing_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("instrument_listings.id"), primary_key=True
    )
    trading_date: Mapped[date] = mapped_column(Date, primary_key=True)
    open: Mapped[Decimal] = mapped_column(Numeric(20, 8))
    high: Mapped[Decimal] = mapped_column(Numeric(20, 8))
    low: Mapped[Decimal] = mapped_column(Numeric(20, 8))
    close: Mapped[Decimal] = mapped_column(Numeric(20, 8))
    adjusted_close: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    volume: Mapped[int] = mapped_column(BigInteger, default=0)
    currency_code: Mapped[str] = mapped_column(String(3), default="USD")
    provider_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("data_providers.id"), nullable=True, index=True
    )
    source_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    data_status: Mapped[str] = mapped_column(String(16), default=DATA_STATUS_FINAL)
    data_version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class LatestDailyPrice(Base):
    __tablename__ = "latest_daily_prices"

    instrument_listing_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("instrument_listings.id"), primary_key=True
    )
    trading_date: Mapped[date] = mapped_column(Date, index=True)
    open: Mapped[Decimal] = mapped_column(Numeric(20, 8))
    high: Mapped[Decimal] = mapped_column(Numeric(20, 8))
    low: Mapped[Decimal] = mapped_column(Numeric(20, 8))
    close: Mapped[Decimal] = mapped_column(Numeric(20, 8))
    adjusted_close: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    volume: Mapped[int] = mapped_column(BigInteger, default=0)
    currency_code: Mapped[str] = mapped_column(String(3), default="USD")
    provider_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    data_status: Mapped[str] = mapped_column(String(16), default=DATA_STATUS_FINAL)
    data_version: Mapped[int] = mapped_column(Integer, default=1)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class IngestionRun(Base):
    __tablename__ = "ingestion_runs"
    __table_args__ = (
        UniqueConstraint(
            "provider_id",
            "exchange_id",
            "job_type",
            "trading_date",
            name="uq_ingestion_run_logical",
        ),
        Index("ix_ingestion_runs_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("data_providers.id"), index=True
    )
    exchange_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("market_exchanges.id"), nullable=True, index=True
    )
    job_type: Mapped[str] = mapped_column(String(64), index=True)
    trading_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(32), default=INGEST_STATUS_QUEUED)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    records_received: Mapped[int] = mapped_column(Integer, default=0)
    records_normalized: Mapped[int] = mapped_column(Integer, default=0)
    records_inserted: Mapped[int] = mapped_column(Integer, default=0)
    records_updated: Mapped[int] = mapped_column(Integer, default=0)
    records_rejected: Mapped[int] = mapped_column(Integer, default=0)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    raw_object_uri: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JsonType, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class IngestionError(Base):
    __tablename__ = "ingestion_errors"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ingestion_run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("ingestion_runs.id"), index=True
    )
    provider_record_identifier: Mapped[str | None] = mapped_column(String(128), nullable=True)
    error_type: Mapped[str] = mapped_column(String(64))
    error_message: Mapped[str] = mapped_column(Text)
    raw_record_json: Mapped[dict[str, Any] | None] = mapped_column(JsonType, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class MarketDataJob(Base):
    __tablename__ = "market_data_jobs"
    __table_args__ = (UniqueConstraint("idempotency_key", name="uq_market_data_jobs_idempotency"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_type: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(32), default=JOB_STATUS_PENDING, index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JsonType, default=dict)
    idempotency_key: Mapped[str] = mapped_column(String(256))
    correlation_id: Mapped[str] = mapped_column(String(64))
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=DEFAULT_MAX_ATTEMPTS)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    result: Mapped[dict[str, Any] | None] = mapped_column(JsonType, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class MarketDataHealth(Base):
    """Last-success / health signal row (singleton key per component)."""

    __tablename__ = "market_data_health"

    component: Mapped[str] = mapped_column(String(64), primary_key=True)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JsonType, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
