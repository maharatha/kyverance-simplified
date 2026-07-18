"""RSRCH-01: grounded canonical research jobs, publication, and API safety."""

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
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("DEV_AUTH", "true")
os.environ.setdefault("QUOTE_MODE", "fixture")
os.environ.setdefault("MARKET_DATA_PROVIDER", "fake")
os.environ.setdefault("MARKET_DATA_ENGINE_ENABLED", "true")
os.environ.setdefault("RESEARCH_ENGINE_ENABLED", "true")
os.environ.setdefault("RESEARCH_JOBS_ENABLED", "true")
os.environ.setdefault("RESEARCH_AI_ENABLED", "false")
os.environ.setdefault("RESEARCH_ARTIFACT_BACKEND", "memory")

from kyverance.config import refresh_settings  # noqa: E402
from kyverance.db.session import Base, get_db  # noqa: E402
from kyverance.main import create_app  # noqa: E402
from kyverance.market_data.jobs.daily_eod import run_daily_eod  # noqa: E402
from kyverance.market_data.jobs.sync_exchanges import sync_exchanges  # noqa: E402
from kyverance.market_data.jobs.sync_instruments import sync_instruments  # noqa: E402
from kyverance.research.artifacts import reset_memory_artifact_store  # noqa: E402
from kyverance.research.cache import reset_research_cache  # noqa: E402
from kyverance.research.constants import (  # noqa: E402
    JOB_FULL_REBUILD,
    JOB_STATUS_DEAD,
    JOB_STATUS_DONE,
    PUB_STATUS_PUBLISHED,
    SECTION_KEYS,
)
from kyverance.research.evidence import EvidenceBundle, collect_internal_evidence  # noqa: E402
from kyverance.research.generate import generate_canonical_report  # noqa: E402
from kyverance.research.jobs import queue  # noqa: E402
from kyverance.research.jobs.scheduler import schedule_once  # noqa: E402
from kyverance.research.jobs.worker import run_once as research_worker_once  # noqa: E402
from kyverance.research.material_change import evaluate_material_change  # noqa: E402
from kyverance.research.metrics import compute_deterministic_metrics  # noqa: E402
from kyverance.research.models import (  # noqa: E402
    ResearchJob,
    ResearchSecurity,
    SecurityResearchLatest,
    SecurityResearchVersion,
)
from kyverance.research.pipeline import run_research_pipeline  # noqa: E402
from kyverance.research.service import get_published_research_ref, get_research_for_symbol  # noqa: E402
from kyverance.research.validate import assert_valid, validate_research_report  # noqa: E402
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


@pytest.fixture(autouse=True)
def _reset_research_adapters():
    reset_research_cache()
    reset_memory_artifact_store()
    refresh_settings()
    yield
    reset_research_cache()
    reset_memory_artifact_store()


def _client_for(db_engine, monkeypatch, **env: str):
    monkeypatch.setenv("APP_ENV", env.get("APP_ENV", "test"))
    monkeypatch.setenv("DEV_AUTH", env.get("DEV_AUTH", "true"))
    monkeypatch.setenv("QUOTE_MODE", "fixture")
    monkeypatch.setenv("MARKET_DATA_PROVIDER", "fake")
    monkeypatch.setenv("RESEARCH_ENGINE_ENABLED", env.get("RESEARCH_ENGINE_ENABLED", "true"))
    monkeypatch.setenv("RESEARCH_JOBS_ENABLED", env.get("RESEARCH_JOBS_ENABLED", "true"))
    monkeypatch.setenv("RESEARCH_AI_ENABLED", "false")
    monkeypatch.setenv("RESEARCH_ARTIFACT_BACKEND", "memory")
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


async def _seed_warehouse(db: Session) -> str:
    await sync_exchanges(db)
    await sync_instruments(db, exchange_canonical="XNAS", limit=10)
    for day in ("2026-07-01", "2026-07-02", "2026-07-06", "2026-07-07", "2026-07-08", "2026-07-09", "2026-07-10"):
        result = await run_daily_eod(db, exchange_canonical="XNAS", trading_date=day)
        assert result["status"] == "PUBLISHED"
    from kyverance.market_data.models import InstrumentListing

    listing = db.query(InstrumentListing).filter(InstrumentListing.is_active.is_(True)).first()
    assert listing is not None
    return listing.ticker


def test_generate_marks_valuation_insufficient_without_fundamentals():
    bundle = EvidenceBundle(
        ticker="AAPL",
        exchange="XNAS",
        market_date=date(2026, 7, 10),
        instrument_id=uuid4(),
        listing_id=uuid4(),
        close=Decimal("190.00"),
        prior_close=Decimal("188.00"),
        volume=1_000_000,
        history=[
            {"tradingDate": "2026-07-06", "close": "185.00", "volume": 1, "dataVersion": 1},
            {"tradingDate": "2026-07-07", "close": "186.00", "volume": 1, "dataVersion": 1},
            {"tradingDate": "2026-07-08", "close": "187.00", "volume": 1, "dataVersion": 1},
            {"tradingDate": "2026-07-09", "close": "188.00", "volume": 1, "dataVersion": 1},
            {"tradingDate": "2026-07-10", "close": "190.00", "volume": 1, "dataVersion": 1},
        ],
        instrument_name="Apple Inc",
        gaps=["filings", "news", "fundamentals"],
    )
    assessment = evaluate_material_change(bundle)
    report = generate_canonical_report(bundle, assessment)
    assert_valid(report)
    assert report["ai_enabled"] is False
    assert report["sections"]["valuation_data_availability"]["status"] == "insufficient_data"
    assert report["sections"]["evidence_gaps"]["status"] == "grounded"
    assert "buy now" not in report["executive_summary"].lower()
    metrics = compute_deterministic_metrics(bundle)
    assert metrics["valuation_ratios"]["pe_ttm"] is None
    assert metrics["close"] == "190.00"


def test_missing_history_marks_trend_insufficient():
    bundle = EvidenceBundle(
        ticker="MSFT",
        exchange="XNAS",
        market_date=date(2026, 7, 10),
        instrument_id=uuid4(),
        listing_id=uuid4(),
        close=Decimal("400.00"),
        prior_close=None,
        volume=100,
        history=[{"tradingDate": "2026-07-10", "close": "400.00", "volume": 100, "dataVersion": 1}],
        gaps=["history", "prior_close"],
    )
    report = generate_canonical_report(bundle, evaluate_material_change(bundle))
    assert report["sections"]["trend_technical_context"]["status"] == "insufficient_data"
    assert report["sections"]["company_market_snapshot"]["status"] in {"grounded", "insufficient_data"}


@pytest.mark.asyncio
async def test_pipeline_rebuild_validate_publish_lineage(db_session: Session, tmp_path, monkeypatch):
    monkeypatch.setenv("RESEARCH_ARTIFACT_BACKEND", "local")
    monkeypatch.setenv("RESEARCH_ARTIFACT_ROOT", str(tmp_path))
    refresh_settings()
    ticker = await _seed_warehouse(db_session)

    first = run_research_pipeline(
        db_session, ticker=ticker, exchange="XNAS", market_date=date(2026, 7, 10)
    )
    assert first["ok"] is True
    assert first["publication_status"] == PUB_STATUS_PUBLISHED
    version_id = first["version_id"]

    version = db_session.get(SecurityResearchVersion, __import__("uuid").UUID(version_id))
    assert version is not None
    assert version.validation_status == "validated"
    assert version.publication_status == PUB_STATUS_PUBLISHED
    assert version.prior_version_id is None
    ptr = db_session.get(SecurityResearchLatest, version.security_id)
    assert ptr is not None and str(ptr.version_id) == version_id

    # Identical evidence reuses published version
    second = run_research_pipeline(
        db_session, ticker=ticker, exchange="XNAS", market_date=date(2026, 7, 10)
    )
    assert second["ok"] is True
    assert second["reused"] is True
    assert second["version_id"] == version_id


@pytest.mark.asyncio
async def test_failed_publication_never_exposes_unpublished(db_session: Session, monkeypatch):
    ticker = await _seed_warehouse(db_session)

    def _boom(*_a, **_k):
        raise RuntimeError("artifact_write_failed")

    monkeypatch.setattr(
        "kyverance.research.pipeline.write_version_artifacts",
        _boom,
    )
    result = run_research_pipeline(
        db_session, ticker=ticker, exchange="XNAS", market_date=date(2026, 7, 10)
    )
    assert result["ok"] is False
    assert db_session.query(SecurityResearchLatest).count() == 0
    unpaid = (
        db_session.query(SecurityResearchVersion)
        .filter(SecurityResearchVersion.publication_status == PUB_STATUS_PUBLISHED)
        .count()
    )
    assert unpaid == 0


@pytest.mark.asyncio
async def test_queue_idempotency_retry_dead_letter(db_session: Session):
    job1 = queue.enqueue_job(
        db_session,
        job_type=JOB_FULL_REBUILD,
        idempotency_key="rebuild:AAPL:2026-07-10",
        payload={"ticker": "AAPL", "exchange": "XNAS"},
    )
    job2 = queue.enqueue_job(
        db_session,
        job_type=JOB_FULL_REBUILD,
        idempotency_key="rebuild:AAPL:2026-07-10",
        payload={"ticker": "AAPL", "exchange": "XNAS"},
    )
    assert job1.id == job2.id

    claimed = queue.claim_next_job(db_session)
    assert claimed is not None
    outcome = queue.fail_job(db_session, claimed, "boom")
    assert outcome == "retry_scheduled"

    # Expire backoff lock and allow another attempt before dead-letter.
    claimed.locked_until = datetime.now(timezone.utc) - timedelta(seconds=1)
    claimed.max_attempts = 2
    db_session.commit()
    claimed2 = queue.claim_next_job(db_session)
    assert claimed2 is not None
    assert int(claimed2.attempts) == 2
    outcome2 = queue.fail_job(db_session, claimed2, "boom-again")
    assert outcome2 == "dead"
    dead = db_session.get(ResearchJob, claimed2.id)
    assert dead is not None and dead.status == JOB_STATUS_DEAD
    assert dead.status != JOB_STATUS_DONE

@pytest.mark.asyncio
async def test_scheduler_enqueues_without_inline_generation(db_session: Session, monkeypatch):
    ticker = await _seed_warehouse(db_session)
    result = run_research_pipeline(
        db_session, ticker=ticker, exchange="XNAS", market_date=date(2026, 7, 10)
    )
    assert result["ok"] is True
    security = db_session.get(ResearchSecurity, __import__("uuid").UUID(result["security_id"]))
    assert security is not None
    security.research_tier = "hot"
    db_session.commit()

    # Force session day to a weekday with lag satisfied
    as_of = datetime(2026, 7, 10, 22, 0, tzinfo=timezone.utc)
    monkeypatch.setattr(
        "kyverance.research.jobs.scheduler.SessionLocal",
        lambda: db_session,
    )
    # Avoid closing the shared fixture session
    monkeypatch.setattr(db_session, "close", lambda: None)

    out = schedule_once(as_of=as_of)
    assert out.get("inline_generation") is False
    assert out.get("ok") is True
    jobs = db_session.query(ResearchJob).all()
    assert any(j.job_type == JOB_FULL_REBUILD for j in jobs)


@pytest.mark.asyncio
async def test_cold_miss_and_worker_smoke(db_engine, monkeypatch):
    app, client, SessionLocal = _client_for(db_engine, monkeypatch)
    db = SessionLocal()
    try:
        ticker = await _seed_warehouse(db)
    finally:
        db.close()

    # Cold miss before any research security exists
    miss = client.get(f"/api/v1/research/securities/{ticker}")
    assert miss.status_code == 202
    body = miss.json()
    assert body["revalidationInProgress"] is True
    assert body["freshnessStatus"] == "REVALIDATING"

    # Worker drains cold job
    monkeypatch.setattr("kyverance.research.jobs.worker.SessionLocal", SessionLocal)
    report = research_worker_once(max_jobs=10)
    assert report["processed"] >= 1
    assert any(j["outcome"] == "done" for j in report["jobs"])

    hit = client.get(f"/api/v1/research/securities/{ticker}")
    assert hit.status_code == 200
    payload = hit.json()
    assert payload["publicationStatus"] == PUB_STATUS_PUBLISHED
    assert payload["ai_enabled"] is False
    for key in SECTION_KEYS:
        assert key in payload["sections"]
        section = payload["sections"][key]
        assert "evidence_coverage" in section
        assert "reasoning_summary" in section
        assert "limitations" in section


@pytest.mark.asyncio
async def test_cache_mismatch_falls_back_to_postgres(db_session: Session):
    ticker = await _seed_warehouse(db_session)
    result = run_research_pipeline(
        db_session, ticker=ticker, exchange="XNAS", market_date=date(2026, 7, 10)
    )
    assert result["ok"] is True
    from kyverance.research.cache import get_research_cache, redis_keys

    cache = get_research_cache()
    keys = redis_keys(result["security_id"])
    cache.set(keys["latest"], "00000000-0000-0000-0000-000000000000")
    payload, status = get_research_for_symbol(db_session, ticker, enqueue_if_missing=False)
    assert status == 200
    assert payload is not None
    assert payload["servedFrom"] == "postgres"
    assert payload["researchVersion"] == result["version_id"]


@pytest.mark.asyncio
async def test_facts_packet_includes_published_research_only(db_engine, monkeypatch):
    from kyverance.agents.service import create_facts_packet
    from kyverance.auth.deps import require_authenticated
    from kyverance.auth.models import DEV_SUBJECT, AuthenticatedSubject
    from kyverance.identity.service import bootstrap_user_on_sign_in
    from kyverance.simulation.models import SimPosition
    from kyverance.simulation.money import money, qty

    app, client, SessionLocal = _client_for(db_engine, monkeypatch)
    db = SessionLocal()
    try:
        ticker = await _seed_warehouse(db)
        result = run_research_pipeline(
            db, ticker=ticker, exchange="XNAS", market_date=date(2026, 7, 10)
        )
        assert result["ok"] is True

        user, _roles, _created = bootstrap_user_on_sign_in(db, entra_oid=DEV_SUBJECT.subject)
        subject = AuthenticatedSubject(
            subject=DEV_SUBJECT.subject,
            user_id=str(user.id),
            display_name=DEV_SUBJECT.display_name,
            roles=DEV_SUBJECT.roles,
            is_dev=True,
        )
        created = client.post("/api/v1/portfolios", json={"name": "Research Portfolio"})
        assert created.status_code == 201
        portfolio_id = created.json()["id"]

        db.add(
            SimPosition(
                id=uuid4(),
                portfolio_id=__import__("uuid").UUID(portfolio_id),
                symbol=ticker,
                quantity=qty("10"),
                avg_cost=money("100"),
            )
        )
        db.commit()

        packet = create_facts_packet(db, subject, __import__("uuid").UUID(portfolio_id))
        kinds = {e.kind for e in packet.evidence_refs}
        assert "canonical_research" in kinds
        assert "plaid" not in kinds
        ref = get_published_research_ref(db, ticker)
        assert ref is not None
        assert ref["publication_status"] == PUB_STATUS_PUBLISHED
    finally:
        db.close()
    _ = app
    _ = require_authenticated

@pytest.mark.asyncio
async def test_research_jobs_do_not_mutate_financial_tables(db_session: Session):
    ticker = await _seed_warehouse(db_session)
    before = {
        "wallets": db_session.query(SimWallet).count(),
        "ledger": db_session.query(WalletLedgerEntry).count(),
        "orders": db_session.query(SimOrder).count(),
        "executions": db_session.query(SimExecution).count(),
    }
    result = run_research_pipeline(
        db_session, ticker=ticker, exchange="XNAS", market_date=date(2026, 7, 10)
    )
    assert result["ok"] is True
    after = {
        "wallets": db_session.query(SimWallet).count(),
        "ledger": db_session.query(WalletLedgerEntry).count(),
        "orders": db_session.query(SimOrder).count(),
        "executions": db_session.query(SimExecution).count(),
    }
    assert before == after


def test_request_handlers_do_not_call_pipeline():
    root = Path(__file__).resolve().parents[1] / "src" / "kyverance"
    route = root / "api" / "routes" / "research.py"
    tree = ast.parse(route.read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            for alias in node.names:
                imported.add(f"{node.module}.{alias.name}")
    forbidden = {
        "kyverance.research.pipeline.run_research_pipeline",
        "kyverance.research.generate.generate_canonical_report",
    }
    assert not (imported & forbidden)


@pytest.mark.asyncio
async def test_ready_includes_research_flags(db_engine, monkeypatch):
    _, client, _ = _client_for(db_engine, monkeypatch)
    body = client.get("/ready").json()
    assert body["checks"]["research_engine"] == "enabled"
    assert body["checks"]["research_jobs"] == "enabled"
    assert body["checks"]["research_ai"] == "disabled"
