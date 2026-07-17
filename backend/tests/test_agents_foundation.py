"""AGENT-01: agent registry, facts packets, deterministic proposals."""

from __future__ import annotations

import os
from collections.abc import Generator
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("DEV_AUTH", "true")
os.environ.setdefault("QUOTE_MODE", "fixture")

from kyverance.agents.constants import (  # noqa: E402
    AUDIT_AGENT_CREATE,
    AUDIT_FACTS_CREATE,
    AUDIT_PROPOSAL_CREATE,
    DISCLOSURE_SIMULATION_SCENARIO,
)
from kyverance.agents.models import Agent, AgentFactsPacket, AgentProposal  # noqa: E402
from kyverance.audit.models import AuditEvent  # noqa: E402
from kyverance.config import refresh_settings  # noqa: E402
from kyverance.db.session import Base, get_db  # noqa: E402
from kyverance.identity.service import bootstrap_user_on_sign_in  # noqa: E402
from kyverance.main import create_app  # noqa: E402
from kyverance.portfolios.models import Portfolio  # noqa: E402
from kyverance.simulation.models import SimOrder, WalletLedgerEntry  # noqa: E402


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


def _client_for(db_engine, monkeypatch, *, app_env: str = "test", dev_auth: str = "true"):
    monkeypatch.setenv("APP_ENV", app_env)
    monkeypatch.setenv("DEV_AUTH", dev_auth)
    monkeypatch.setenv("QUOTE_MODE", "fixture")
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


def _create_portfolio(client: TestClient, name: str = "Agent book") -> str:
    response = client.post("/api/v1/portfolios", json={"name": name})
    assert response.status_code == 201
    return response.json()["id"]


def test_agent_create_list_and_idempotency(db_engine, monkeypatch):
    application, client, _SessionLocal = _client_for(db_engine, monkeypatch)
    portfolio_id = _create_portfolio(client)

    empty = client.get(f"/api/v1/portfolios/{portfolio_id}/agents")
    assert empty.status_code == 200
    assert empty.json()["agents"] == []
    assert "No agents yet" in empty.json()["empty_state"]

    created = client.post(
        f"/api/v1/portfolios/{portfolio_id}/agents",
        json={
            "name": "Research scout",
            "purpose": "Draft rebalance scenarios from authorized facts",
            "capabilities": ["research", "scenario"],
        },
        headers={"Idempotency-Key": "agent-1"},
    )
    assert created.status_code == 201
    body = created.json()
    assert body["name"] == "Research scout"
    assert body["can_execute_orders"] is False
    assert body["model_provider"] == "fixture"
    assert DISCLOSURE_SIMULATION_SCENARIO in body["disclosure"]

    again = client.post(
        f"/api/v1/portfolios/{portfolio_id}/agents",
        json={
            "name": "Different name",
            "purpose": "Should not create a second row",
            "capabilities": [],
        },
        headers={"Idempotency-Key": "agent-1"},
    )
    assert again.status_code == 201
    assert again.json()["id"] == body["id"]

    listed = client.get(f"/api/v1/portfolios/{portfolio_id}/agents")
    assert listed.status_code == 200
    assert len(listed.json()["agents"]) == 1

    application.dependency_overrides.clear()
    refresh_settings()


def test_ownership_isolation_for_agents_facts_proposals(db_engine, monkeypatch):
    application, client, SessionLocal = _client_for(db_engine, monkeypatch)
    portfolio_id = _create_portfolio(client)

    agent = client.post(
        f"/api/v1/portfolios/{portfolio_id}/agents",
        json={"name": "Mine", "purpose": "Private agent"},
    ).json()
    facts = client.post(f"/api/v1/portfolios/{portfolio_id}/facts-packets").json()
    proposal = client.post(
        f"/api/v1/portfolios/{portfolio_id}/agents/{agent['id']}/proposals",
        json={"facts_packet_id": facts["id"]},
        headers={"Idempotency-Key": "prop-1"},
    ).json()

    foreign_portfolio_id = uuid4()
    foreign_agent_id = uuid4()
    foreign_facts_id = uuid4()
    foreign_proposal_id = uuid4()

    db = SessionLocal()
    foreign_user, _, _ = bootstrap_user_on_sign_in(db, entra_oid="foreign-owner-001")

    # Insert foreign-owned rows directly so the authenticated dev user cannot see them.
    from kyverance.simulation.models import SimWallet
    from kyverance.simulation.money import money
    from kyverance.simulation.constants import (
        PORTFOLIO_PROVENANCE_SIMULATED,
        PORTFOLIO_STATUS_ACTIVE,
        PORTFOLIO_VISIBILITY_PRIVATE,
        VIRTUAL_CURRENCY_CODE,
    )

    foreign_portfolio = Portfolio(
        id=foreign_portfolio_id,
        owner_user_id=foreign_user.id,
        name="Foreign",
        visibility=PORTFOLIO_VISIBILITY_PRIVATE,
        provenance=PORTFOLIO_PROVENANCE_SIMULATED,
        status=PORTFOLIO_STATUS_ACTIVE,
        currency_code=VIRTUAL_CURRENCY_CODE,
    )
    db.add(foreign_portfolio)
    db.flush()
    db.add(
        SimWallet(
            portfolio_id=foreign_portfolio.id,
            owner_user_id=foreign_user.id,
            currency_code=VIRTUAL_CURRENCY_CODE,
            balance=money("1000"),
            complimentary_balance=money("1000"),
            version=1,
        )
    )
    db.add(
        Agent(
            id=foreign_agent_id,
            portfolio_id=foreign_portfolio_id,
            owner_user_id=foreign_user.id,
            name="Foreign agent",
            purpose="Not yours",
            capabilities_json=[],
            status="active",
            model_provider="fixture",
            model_name="deterministic-v1",
            model_version="1.0.0",
            prompt_template_version="agent-01-v1",
            budget_tokens=100,
            budget_usd_cents=0,
            metadata_json={},
        )
    )
    from datetime import UTC, datetime

    now = datetime.now(UTC)
    db.add(
        AgentFactsPacket(
            id=foreign_facts_id,
            portfolio_id=foreign_portfolio_id,
            owner_user_id=foreign_user.id,
            data_as_of=now,
            evidence_refs_json=[],
            holdings_json=[],
            cash_json={},
            risk_inputs_json={},
            checksum="a" * 64,
        )
    )
    db.add(
        AgentProposal(
            id=foreign_proposal_id,
            agent_id=foreign_agent_id,
            portfolio_id=foreign_portfolio_id,
            owner_user_id=foreign_user.id,
            facts_packet_id=foreign_facts_id,
            facts_checksum="a" * 64,
            proposal_type="hold_scenario",
            horizon="30d",
            assumptions_json=[],
            actions_json=[],
            draft_allocation_json={},
            evidence_refs_json=[],
            confidence="low",
            limitations="n/a",
            safety_decision="allowed_for_review",
            model_provider="fixture",
            model_name="deterministic-v1",
            model_version="1.0.0",
            prompt_template_version="agent-01-v1",
            cost_usd_cents=0,
            latency_ms=0,
            status="ready_for_review",
            summary="secret",
            data_as_of=now,
        )
    )
    db.commit()
    db.close()

    assert client.get(f"/api/v1/portfolios/{foreign_portfolio_id}/agents").status_code == 404
    assert (
        client.get(f"/api/v1/portfolios/{foreign_portfolio_id}/agents/{foreign_agent_id}").status_code
        == 404
    )
    assert (
        client.get(
            f"/api/v1/portfolios/{foreign_portfolio_id}/facts-packets/{foreign_facts_id}"
        ).status_code
        == 404
    )
    assert (
        client.get(
            f"/api/v1/portfolios/{foreign_portfolio_id}/proposals/{foreign_proposal_id}"
        ).status_code
        == 404
    )
    assert client.get(f"/api/v1/agent-proposals/{foreign_proposal_id}").status_code == 404

    # Own resources still readable
    assert client.get(f"/api/v1/portfolios/{portfolio_id}/agents/{agent['id']}").status_code == 200
    assert (
        client.get(f"/api/v1/portfolios/{portfolio_id}/facts-packets/{facts['id']}").status_code
        == 200
    )
    assert (
        client.get(f"/api/v1/portfolios/{portfolio_id}/proposals/{proposal['id']}").status_code
        == 200
    )
    assert client.get(f"/api/v1/agent-proposals/{proposal['id']}").status_code == 200

    application.dependency_overrides.clear()
    refresh_settings()


def test_facts_checksum_stable_and_immutable(db_engine, monkeypatch):
    application, client, SessionLocal = _client_for(db_engine, monkeypatch)
    portfolio_id = _create_portfolio(client)

    first = client.post(
        f"/api/v1/portfolios/{portfolio_id}/facts-packets",
        headers={"Idempotency-Key": "facts-1"},
    )
    assert first.status_code == 201
    body = first.json()
    assert len(body["checksum"]) == 64
    assert body["immutable"] is True
    assert body["cash"]["cash_balance"] == "1000.0000"

    again = client.post(
        f"/api/v1/portfolios/{portfolio_id}/facts-packets",
        headers={"Idempotency-Key": "facts-1"},
    )
    assert again.status_code == 201
    assert again.json()["id"] == body["id"]
    assert again.json()["checksum"] == body["checksum"]

    # Live wallet change must not mutate the stored facts packet.
    db = SessionLocal()
    packet = db.query(AgentFactsPacket).filter(AgentFactsPacket.id == UUID(body["id"])).one()
    original_checksum = packet.checksum
    original_cash = dict(packet.cash_json)
    db.close()

    preview = client.post(
        f"/api/v1/portfolios/{portfolio_id}/orders/preview",
        json={"symbol": "AAPL", "side": "buy", "quantity": "1"},
    )
    assert preview.status_code == 200
    confirm = client.post(
        f"/api/v1/portfolios/{portfolio_id}/orders/confirm",
        json={"preview_id": preview.json()["preview_id"]},
        headers={"Idempotency-Key": "buy-after-facts"},
    )
    assert confirm.status_code == 200

    fetched = client.get(f"/api/v1/portfolios/{portfolio_id}/facts-packets/{body['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["checksum"] == original_checksum
    assert fetched.json()["cash"] == original_cash

    application.dependency_overrides.clear()
    refresh_settings()


def test_fixture_proposal_disclosures_idempotency_and_audit(db_engine, monkeypatch):
    application, client, SessionLocal = _client_for(db_engine, monkeypatch)
    portfolio_id = _create_portfolio(client)
    agent_id = client.post(
        f"/api/v1/portfolios/{portfolio_id}/agents",
        json={"name": "Fixture agent", "purpose": "Generate scenarios"},
        headers={"Idempotency-Key": "agent-fx"},
    ).json()["id"]

    created = client.post(
        f"/api/v1/portfolios/{portfolio_id}/agents/{agent_id}/proposals",
        json={"horizon": "14d"},
        headers={"Idempotency-Key": "proposal-fx"},
    )
    assert created.status_code == 201
    body = created.json()
    assert body["scenario_label"] == "Simulation scenario"
    assert body["can_execute"] is False
    assert body["can_auto_trade"] is False
    assert body["review_cta"] == "Review proposal"
    assert "Simulation scenario" in body["disclosure"] or "simulation scenario" in body["disclosure"].lower()
    assert body["data_as_of"]
    assert body["evidence_refs"]
    assert body["assumptions"]
    assert body["horizon"] == "14d"
    assert body["limitations"]
    assert body["model_provider"] == "fixture"
    assert body["model_version"]
    assert body["safety_decision"] == "allowed_for_review"
    assert body["facts_checksum"]
    assert len(body["facts_checksum"]) == 64

    again = client.post(
        f"/api/v1/portfolios/{portfolio_id}/agents/{agent_id}/proposals",
        json={"horizon": "90d"},
        headers={"Idempotency-Key": "proposal-fx"},
    )
    assert again.status_code == 201
    assert again.json()["id"] == body["id"]
    assert again.json()["horizon"] == "14d"

    db = SessionLocal()
    actions = {row.action for row in db.query(AuditEvent).all()}
    assert AUDIT_AGENT_CREATE in actions
    assert AUDIT_FACTS_CREATE in actions
    assert AUDIT_PROPOSAL_CREATE in actions
    db.close()

    application.dependency_overrides.clear()
    refresh_settings()


def test_proposal_apis_cannot_mutate_orders_or_ledger(db_engine, monkeypatch):
    application, client, SessionLocal = _client_for(db_engine, monkeypatch)
    portfolio_id = _create_portfolio(client)
    agent_id = client.post(
        f"/api/v1/portfolios/{portfolio_id}/agents",
        json={"name": "Safe agent", "purpose": "Draft only"},
    ).json()["id"]

    db = SessionLocal()
    ledger_before = db.query(func.count(WalletLedgerEntry.id)).scalar()
    orders_before = db.query(func.count(SimOrder.id)).scalar()
    db.close()

    proposal = client.post(
        f"/api/v1/portfolios/{portfolio_id}/agents/{agent_id}/proposals",
        headers={"Idempotency-Key": "no-mutate"},
    )
    assert proposal.status_code == 201
    assert proposal.json()["can_execute"] is False

    # No execute/confirm endpoints exist under agent routes.
    routes = {route.path for route in application.routes if hasattr(route, "path")}
    forbidden_fragments = ("/execute", "/auto-trade", "/confirm-order", "/submit-order")
    agent_paths = [path for path in routes if "agent" in path or "/proposals" in path]
    for path in agent_paths:
        for fragment in forbidden_fragments:
            assert fragment not in path

    db = SessionLocal()
    ledger_after = db.query(func.count(WalletLedgerEntry.id)).scalar()
    orders_after = db.query(func.count(SimOrder.id)).scalar()
    cash = client.get(f"/api/v1/portfolios/{portfolio_id}").json()["wallet"]["cash_balance"]
    db.close()

    assert ledger_after == ledger_before
    assert orders_after == orders_before
    assert cash == "1000.0000"

    application.dependency_overrides.clear()
    refresh_settings()


def test_validation_and_auth_required(db_engine, monkeypatch):
    application, client, _SessionLocal = _client_for(db_engine, monkeypatch)
    portfolio_id = _create_portfolio(client)

    bad = client.post(
        f"/api/v1/portfolios/{portfolio_id}/agents",
        json={"name": "", "purpose": "x"},
    )
    assert bad.status_code == 422

    agent_id = client.post(
        f"/api/v1/portfolios/{portfolio_id}/agents",
        json={"name": "Valid", "purpose": "Valid purpose"},
    ).json()["id"]

    bad_type = client.post(
        f"/api/v1/portfolios/{portfolio_id}/agents/{agent_id}/proposals",
        json={"proposal_type": "execute_trades"},
    )
    assert bad_type.status_code == 400

    application.dependency_overrides.clear()
    refresh_settings()

    application, client, _SessionLocal = _client_for(
        db_engine, monkeypatch, app_env="production", dev_auth="false"
    )
    denied = client.get(f"/api/v1/portfolios/{portfolio_id}/agents")
    assert denied.status_code == 401
    application.dependency_overrides.clear()
    refresh_settings()
