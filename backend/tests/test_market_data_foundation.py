"""MRKT-01: market-data warehouse, jobs, fake ingest, internal reads."""

from __future__ import annotations

import ast
import os
from collections.abc import Generator
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("DEV_AUTH", "true")
os.environ.setdefault("QUOTE_MODE", "fixture")
os.environ.setdefault("MARKET_DATA_PROVIDER", "fake")
os.environ.setdefault("MARKET_DATA_ENGINE_ENABLED", "true")
os.environ.setdefault("MARKET_DATA_JOBS_ENABLED", "true")

from kyverance.config import refresh_settings  # noqa: E402
from kyverance.db.session import Base, get_db  # noqa: E402
from kyverance.main import create_app  # noqa: E402
from kyverance.market_data.constants import (  # noqa: E402
    JOB_DAILY_EOD,
    JOB_STATUS_DEAD,
    JOB_STATUS_DONE,
)
from kyverance.market_data.dto import NormalizedDailyPrice  # noqa: E402
from kyverance.market_data.ingest.validate import validate_batch  # noqa: E402
from kyverance.market_data.jobs import queue  # noqa: E402
from kyverance.market_data.jobs.correction import run_correction  # noqa: E402
from kyverance.market_data.jobs.daily_eod import run_daily_eod  # noqa: E402
from kyverance.market_data.jobs.reconcile import run_reconcile  # noqa: E402
from kyverance.market_data.jobs.scheduler import ensure_weekday_calendar, schedule_once  # noqa: E402
from kyverance.market_data.jobs.sync_exchanges import sync_exchanges  # noqa: E402
from kyverance.market_data.jobs.sync_instruments import sync_instruments  # noqa: E402
from kyverance.market_data.models import (  # noqa: E402
    DailyPrice,
    DataProvider,
    IngestionRun,
    InstrumentListing,
    LatestDailyPrice,
    MarketDataJob,
    MarketExchange,
)
from kyverance.market_data.providers.base import ProviderNotConfiguredError  # noqa: E402
from kyverance.market_data.providers.registry import get_market_data_provider  # noqa: E402
from kyverance.market_data.service import InternalDataUnavailable, get_latest_by_symbol  # noqa: E402
from kyverance.simulation.models import (  # noqa: E402
    SimExecution,
    SimOrder,
    SimWallet,
    WalletLedgerEntry,
)


@pytest.fixture()
def db_engine():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture()
def db_session(db_engine) -> Generator[Session, None, None]:
    SessionLocal = sessionmaker(bind=db_engine, autocommit=False, autoflush=False, class_=Session)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def _client_for(db_engine, monkeypatch, **env: str):
    monkeypatch.setenv("APP_ENV", env.get("APP_ENV", "test"))
    monkeypatch.setenv("DEV_AUTH", env.get("DEV_AUTH", "true"))
    monkeypatch.setenv("QUOTE_MODE", "fixture")
    monkeypatch.setenv("MARKET_DATA_PROVIDER", env.get("MARKET_DATA_PROVIDER", "fake"))
    monkeypatch.setenv("MARKET_DATA_ENGINE_ENABLED", env.get("MARKET_DATA_ENGINE_ENABLED", "true"))
    monkeypatch.setenv("MARKET_DATA_JOBS_ENABLED", env.get("MARKET_DATA_JOBS_ENABLED", "true"))
    monkeypatch.setenv(
        "MARKET_DATA_STALE_TOLERANCE_MINUTES",
        env.get("MARKET_DATA_STALE_TOLERANCE_MINUTES", "1440"),
    )
    refresh_settings()

    SessionLocal = sessionmaker(bind=db_engine, autocommit=False, autoflush=False, class_=Session)

    def _override_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    application = create_app()
    application.dependency_overrides[get_db] = _override_db
    return application, TestClient(application), SessionLocal


async def _seed_warehouse(db: Session) -> None:
    await sync_exchanges(db)
    await sync_instruments(db, exchange_canonical="XNAS", limit=10)
    result = await run_daily_eod(db, exchange_canonical="XNAS", trading_date="2026-07-01")
    assert result["status"] == "PUBLISHED"


def test_validate_rejects_bad_ohlc():
    bad = NormalizedDailyPrice(
        instrument_listing_id=str(uuid4()),
        trading_date=date(2026, 7, 1),
        open=Decimal("10"),
        high=Decimal("9"),
        low=Decimal("11"),
        close=Decimal("10"),
        adjusted_close=Decimal("10"),
        volume=100,
        currency_code="USD",
        provider_symbol="BAD",
        provider_exchange_code="US",
    )
    accepted, issues, publish_ok = validate_batch([bad])
    assert not publish_ok
    assert accepted == []
    assert any(i.error_type == "high_below_low" for i in issues)


@pytest.mark.asyncio
async def test_fake_provider_ingest_normalize_publish_and_idempotent(db_session):
    await _seed_warehouse(db_session)
    prices = db_session.query(DailyPrice).count()
    latest = db_session.query(LatestDailyPrice).count()
    assert prices >= 3
    assert latest >= 3

    again = await run_daily_eod(db_session, exchange_canonical="XNAS", trading_date="2026-07-01")
    assert again["status"] == "PUBLISHED"
    runs = (
        db_session.query(IngestionRun)
        .filter(IngestionRun.job_type == JOB_DAILY_EOD, IngestionRun.trading_date == date(2026, 7, 1))
        .count()
    )
    assert runs == 1
    assert db_session.query(DailyPrice).count() == prices


@pytest.mark.asyncio
async def test_correction_bumps_version_and_keeps_provenance(db_session):
    await _seed_warehouse(db_session)
    listing = db_session.query(InstrumentListing).filter(InstrumentListing.ticker == "AAPL").one()
    before = db_session.get(DailyPrice, (listing.id, date(2026, 7, 1)))
    assert before is not None
    assert before.data_version == 1
    before.close = Decimal("999.00")
    db_session.commit()

    result = await run_correction(db_session, exchange_canonical="XNAS", trading_date="2026-07-01")
    assert result["status"] == "PUBLISHED"
    after = db_session.get(DailyPrice, (listing.id, date(2026, 7, 1)))
    assert after is not None
    assert after.data_version == 2
    assert after.close != Decimal("999.00")
    assert after.provider_id is not None
    corr_runs = (
        db_session.query(IngestionRun)
        .filter(IngestionRun.job_type == "CORRECTION", IngestionRun.trading_date == date(2026, 7, 1))
        .count()
    )
    assert corr_runs == 1


@pytest.mark.asyncio
async def test_reconcile_alerts_and_ok(db_session):
    await _seed_warehouse(db_session)
    ok = run_reconcile(db_session, exchange_canonical="XNAS", trading_date="2026-07-01")
    assert ok["status"] == "ok"
    alert = run_reconcile(db_session, exchange_canonical="XNAS", trading_date="2026-07-03")
    assert alert["status"] == "alert"
    assert "missing_or_unpublished_daily_eod" in alert["alerts"]


def test_queue_claim_retry_dead_letter(db_session, monkeypatch):
    monkeypatch.setenv("MARKET_DATA_JOB_LOCK_SECONDS", "60")
    refresh_settings()
    job = queue.enqueue_job(
        db_session,
        job_type=JOB_DAILY_EOD,
        idempotency_key="daily-eod:XNAS:2026-07-01",
        payload={"exchange": "XNAS", "trading_date": "2026-07-01"},
    )
    again = queue.enqueue_job(
        db_session,
        job_type=JOB_DAILY_EOD,
        idempotency_key="daily-eod:XNAS:2026-07-01",
        payload={"exchange": "XNAS", "trading_date": "2026-07-01"},
    )
    assert again.id == job.id
    assert job.correlation_id

    claimed = queue.claim_next_job(db_session)
    assert claimed is not None
    assert claimed.id == job.id
    assert claimed.attempts == 1

    for _ in range(4):
        outcome = queue.fail_job(db_session, claimed, "boom")
        assert outcome == "retry_scheduled"
        claimed.locked_until = datetime.now(timezone.utc) - timedelta(seconds=1)
        db_session.commit()
        claimed = queue.claim_next_job(db_session)
        assert claimed is not None

    outcome = queue.fail_job(db_session, claimed, "final boom")
    assert outcome == "dead"
    dead = db_session.get(MarketDataJob, job.id)
    assert dead is not None
    assert dead.status == JOB_STATUS_DEAD


def test_scheduler_idempotency_and_calendar(db_session, monkeypatch):
    monkeypatch.setenv("MARKET_DATA_JOBS_ENABLED", "true")
    refresh_settings()
    dp = DataProvider(id=uuid4(), code="fake", name="fake", provider_type="eod", is_active=True)
    ex = MarketExchange(
        id=uuid4(),
        mic_code="XNAS",
        canonical_code="XNAS",
        name="NASDAQ",
        country_code="US",
        timezone="America/New_York",
        regular_close_time="16:00",
        default_data_availability_delay_minutes=0,
        is_active=True,
    )
    db_session.add_all([dp, ex])
    db_session.commit()

    from kyverance.market_data.models import ExchangeTradingDay

    created = ensure_weekday_calendar(db_session, ex, 2026)
    assert created > 200
    weekend = (
        db_session.query(ExchangeTradingDay)
        .filter(
            ExchangeTradingDay.exchange_id == ex.id,
            ExchangeTradingDay.trading_date == date(2026, 7, 4),  # Saturday
        )
        .one_or_none()
    )
    assert weekend is None

    # After close + delay on a weekday session
    now = datetime(2026, 7, 1, 22, 0, tzinfo=timezone.utc)  # after 16:00 ET
    first = schedule_once(db_session, now=now)
    second = schedule_once(db_session, now=now)
    assert any(k.startswith("daily-eod:XNAS:") for k in first["enqueued"])
    assert db_session.query(MarketDataJob).count() == len(set(first["enqueued"]))
    # Idempotent: second schedule does not duplicate rows
    assert db_session.query(MarketDataJob).count() == len(set(second["enqueued"]))


@pytest.mark.asyncio
async def test_internal_reads_unavailable_and_stale(db_session, monkeypatch):
    await _seed_warehouse(db_session)
    quote = get_latest_by_symbol(db_session, "XNAS", "AAPL")
    assert quote["ticker"] == "AAPL"
    assert quote["close"]
    assert quote["isStale"] is False

    with pytest.raises(InternalDataUnavailable):
        get_latest_by_symbol(db_session, "XNAS", "NOPE")

    listing = db_session.query(InstrumentListing).filter(InstrumentListing.ticker == "AAPL").one()
    latest = db_session.get(LatestDailyPrice, listing.id)
    assert latest is not None
    latest.updated_at = datetime.now(timezone.utc) - timedelta(days=3)
    db_session.commit()
    monkeypatch.setenv("MARKET_DATA_STALE_TOLERANCE_MINUTES", "60")
    refresh_settings()
    stale = get_latest_by_symbol(db_session, "XNAS", "AAPL")
    assert stale["isStale"] is True
    assert stale["availability"] == "stale"


@pytest.mark.asyncio
async def test_jobs_do_not_mutate_simulation_financial_tables(db_session):
    before = {
        "wallets": db_session.query(SimWallet).count(),
        "ledger": db_session.query(WalletLedgerEntry).count(),
        "orders": db_session.query(SimOrder).count(),
        "executions": db_session.query(SimExecution).count(),
    }
    await _seed_warehouse(db_session)
    await run_correction(db_session, exchange_canonical="XNAS", trading_date="2026-07-01")
    run_reconcile(db_session, exchange_canonical="XNAS", trading_date="2026-07-01")
    after = {
        "wallets": db_session.query(SimWallet).count(),
        "ledger": db_session.query(WalletLedgerEntry).count(),
        "orders": db_session.query(SimOrder).count(),
        "executions": db_session.query(SimExecution).count(),
    }
    assert before == after


def test_read_and_api_modules_never_import_providers():
    root = Path(__file__).resolve().parents[1] / "src" / "kyverance"
    files = [
        root / "market_data" / "service.py",
        root / "api" / "routes" / "market_data.py",
    ]
    forbidden = {"kyverance.market_data.providers", "providers.registry", "providers.fake", "providers.live"}
    for path in files:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert not any(f in alias.name for f in forbidden), path
            if isinstance(node, ast.ImportFrom) and node.module:
                assert not any(f in node.module for f in forbidden), path


def test_live_provider_disabled_without_secrets(monkeypatch):
    monkeypatch.setenv("MARKET_DATA_PROVIDER", "live")
    monkeypatch.setenv("MARKET_DATA_LIVE_API_TOKEN", "")
    refresh_settings()
    with pytest.raises(ProviderNotConfiguredError):
        get_market_data_provider()


@pytest.mark.asyncio
async def test_api_latest_history_kill_switch_and_ready(db_engine, monkeypatch):
    application, client, SessionLocal = _client_for(db_engine, monkeypatch)
    db = SessionLocal()
    try:
        await _seed_warehouse(db)
    finally:
        db.close()

    ready = client.get("/ready")
    assert ready.status_code == 200
    body = ready.json()
    assert body["status"] == "ok"
    assert body["checks"]["market_data_engine"] == "enabled"
    assert body["checks"]["market_data_ingest_provider"] == "fake"

    latest = client.get("/api/v1/market-data/exchanges/XNAS/symbols/AAPL/latest")
    assert latest.status_code == 200
    payload = latest.json()
    assert payload["ticker"] == "AAPL"
    assert payload["close"]
    assert "dataVersion" in payload

    history = client.get(
        "/api/v1/market-data/exchanges/XNAS/symbols/AAPL/history",
        params={"from": "2026-07-01", "to": "2026-07-02"},
    )
    assert history.status_code == 200
    assert len(history.json()["points"]) >= 1

    missing = client.get("/api/v1/market-data/exchanges/XNAS/symbols/ZZZZ/latest")
    assert missing.status_code == 503
    assert missing.json()["detail"]["code"] == "internal_data_unavailable"

    monkeypatch.setenv("MARKET_DATA_ENGINE_ENABLED", "false")
    refresh_settings()
    disabled = client.get("/api/v1/market-data/exchanges/XNAS/symbols/AAPL/latest")
    assert disabled.status_code == 503
    assert disabled.json()["detail"] == "market_data_disabled"

    # Kill switch must not affect portfolio pages / health
    health = client.get("/health")
    assert health.status_code == 200
    portfolios = client.get("/api/v1/portfolios")
    assert portfolios.status_code == 200


def test_queue_complete_sets_done(db_session):
    job = queue.enqueue_job(
        db_session,
        job_type="RECONCILE",
        idempotency_key="reconcile:XNAS:2026-07-01",
        payload={"exchange": "XNAS", "trading_date": "2026-07-01"},
    )
    claimed = queue.claim_next_job(db_session)
    assert claimed is not None
    queue.complete_job(db_session, claimed, {"status": "ok"})
    row = db_session.get(MarketDataJob, job.id)
    assert row is not None
    assert row.status == JOB_STATUS_DONE
    assert row.result["status"] == "ok"


def test_market_tables_registered(db_engine):
    names = set(inspect(db_engine).get_table_names())
    for required in {
        "data_providers",
        "market_exchanges",
        "instrument_listings",
        "daily_prices",
        "latest_daily_prices",
        "ingestion_runs",
        "ingestion_errors",
        "market_data_jobs",
        "market_data_health",
    }:
        assert required in names
