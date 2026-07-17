"""FORK-01: immutable versions, publish consent, independent forks."""

from __future__ import annotations

import os
from collections.abc import Generator
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("DEV_AUTH", "true")
os.environ.setdefault("QUOTE_MODE", "fixture")

from kyverance.audit.models import AuditEvent  # noqa: E402
from kyverance.config import refresh_settings  # noqa: E402
from kyverance.db.session import Base, get_db  # noqa: E402
from kyverance.identity.roles import RoleKey  # noqa: E402
from kyverance.identity.service import bootstrap_user_on_sign_in, grant_role  # noqa: E402
from kyverance.main import create_app  # noqa: E402
from kyverance.portfolios.constants import (  # noqa: E402
    LICENSE_PUBLIC_FORK_ALLOWED,
    LICENSE_VIEW_ONLY,
    VERSION_STATUS_PUBLISHED,
)
from kyverance.portfolios.models import Portfolio, PortfolioFork, PortfolioVersion  # noqa: E402
from kyverance.simulation.models import SimPosition, SimPositionLot, SimWallet  # noqa: E402
from kyverance.simulation.money import money  # noqa: E402


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


def _grant_creator(SessionLocal) -> None:
    db = SessionLocal()
    user, _, _ = bootstrap_user_on_sign_in(db, entra_oid="dev-user-001")
    grant_role(db, user=user, role_key=RoleKey.CREATOR.value, actor_subject="admin-001")
    db.close()


def test_version_snapshot_is_immutable_after_live_changes(db_engine, monkeypatch):
    application, client, SessionLocal = _client_for(db_engine, monkeypatch)

    created = client.post(
        "/api/v1/portfolios",
        json={"name": "Core", "thesis": "Hold quality compounders", "agent_config_ref": "agent-cfg-1"},
    )
    assert created.status_code == 201
    portfolio_id = created.json()["id"]
    assert created.json()["thesis"] == "Hold quality compounders"

    preview = client.post(
        f"/api/v1/portfolios/{portfolio_id}/orders/preview",
        json={"symbol": "AAPL", "side": "buy", "quantity": "1"},
    )
    assert preview.status_code == 200
    confirm = client.post(
        f"/api/v1/portfolios/{portfolio_id}/orders/confirm",
        json={"preview_id": preview.json()["preview_id"]},
        headers={"Idempotency-Key": "buy-aapl-1"},
    )
    assert confirm.status_code == 200

    version = client.post(
        f"/api/v1/portfolios/{portfolio_id}/versions",
        headers={"Idempotency-Key": "v1"},
    )
    assert version.status_code == 201
    body = version.json()
    assert body["version_number"] == 1
    assert body["thesis"] == "Hold quality compounders"
    assert body["agent_config_ref"] == "agent-cfg-1"
    assert body["status"] == "draft"
    assert body["visibility"] == "private"
    assert len(body["checksum"]) == 64
    assert any(h["symbol"] == "AAPL" for h in body["holdings"])
    original_checksum = body["checksum"]
    original_holdings = body["holdings"]

    patched = client.patch(
        f"/api/v1/portfolios/{portfolio_id}",
        json={"thesis": "Changed thesis after snapshot"},
    )
    assert patched.status_code == 200
    assert patched.json()["thesis"] == "Changed thesis after snapshot"

    listed = client.get(f"/api/v1/portfolios/{portfolio_id}/versions")
    assert listed.status_code == 200
    assert listed.json()["versions"][0]["checksum"] == original_checksum
    assert listed.json()["versions"][0]["thesis"] == "Hold quality compounders"
    assert listed.json()["versions"][0]["holdings"] == original_holdings

    # Idempotent create
    again = client.post(
        f"/api/v1/portfolios/{portfolio_id}/versions",
        headers={"Idempotency-Key": "v1"},
    )
    assert again.status_code == 201
    assert again.json()["id"] == body["id"]

    application.dependency_overrides.clear()
    refresh_settings()


def test_publish_requires_creator_consent_and_blocks_policy_mutation(db_engine, monkeypatch):
    application, client, SessionLocal = _client_for(db_engine, monkeypatch)

    portfolio_id = client.post("/api/v1/portfolios", json={"name": "Publish me"}).json()["id"]
    version_id = client.post(f"/api/v1/portfolios/{portfolio_id}/versions").json()["id"]

    denied = client.post(
        f"/api/v1/portfolios/{portfolio_id}/versions/{version_id}/publish",
        json={
            "visibility": "public",
            "license": LICENSE_PUBLIC_FORK_ALLOWED,
            "provenance": "simulated",
            "consent_acknowledged": True,
            "disclosure_acknowledged": True,
        },
    )
    assert denied.status_code == 403

    _grant_creator(SessionLocal)

    no_consent = client.post(
        f"/api/v1/portfolios/{portfolio_id}/versions/{version_id}/publish",
        json={
            "visibility": "public",
            "license": LICENSE_PUBLIC_FORK_ALLOWED,
            "provenance": "simulated",
            "consent_acknowledged": False,
            "disclosure_acknowledged": True,
        },
    )
    assert no_consent.status_code == 400

    no_disclosure = client.post(
        f"/api/v1/portfolios/{portfolio_id}/versions/{version_id}/publish",
        json={
            "visibility": "public",
            "license": LICENSE_PUBLIC_FORK_ALLOWED,
            "provenance": "simulated",
            "consent_acknowledged": True,
            "disclosure_acknowledged": False,
        },
    )
    assert no_disclosure.status_code == 400

    published = client.post(
        f"/api/v1/portfolios/{portfolio_id}/versions/{version_id}/publish",
        json={
            "visibility": "public",
            "license": LICENSE_PUBLIC_FORK_ALLOWED,
            "provenance": "simulated",
            "consent_acknowledged": True,
            "disclosure_acknowledged": True,
        },
    )
    assert published.status_code == 200
    pub = published.json()
    assert pub["status"] == VERSION_STATUS_PUBLISHED
    assert pub["visibility"] == "public"
    assert pub["license"] == LICENSE_PUBLIC_FORK_ALLOWED
    assert pub["consent_acknowledged"] is True
    assert pub["fork_allowed"] is True
    assert pub["disclosure"]

    conflict = client.post(
        f"/api/v1/portfolios/{portfolio_id}/versions/{version_id}/publish",
        json={
            "visibility": "public",
            "license": LICENSE_VIEW_ONLY,
            "provenance": "simulated",
            "consent_acknowledged": True,
            "disclosure_acknowledged": True,
        },
    )
    assert conflict.status_code == 409

    db = SessionLocal()
    actions = {e.action for e in db.query(AuditEvent).all()}
    assert "portfolio.version.publish" in actions
    db.close()

    application.dependency_overrides.clear()
    refresh_settings()


def test_fork_creates_independent_wallet_and_lineage(db_engine, monkeypatch):
    application, client, SessionLocal = _client_for(db_engine, monkeypatch)
    _grant_creator(SessionLocal)

    source = client.post(
        "/api/v1/portfolios",
        json={"name": "Source book", "thesis": "Source thesis"},
    ).json()
    source_id = source["id"]
    preview = client.post(
        f"/api/v1/portfolios/{source_id}/orders/preview",
        json={"symbol": "MSFT", "side": "buy", "quantity": "2"},
    )
    assert preview.status_code == 200
    assert (
        client.post(
            f"/api/v1/portfolios/{source_id}/orders/confirm",
            json={"preview_id": preview.json()["preview_id"]},
            headers={"Idempotency-Key": "buy-msft"},
        ).status_code
        == 200
    )

    version = client.post(f"/api/v1/portfolios/{source_id}/versions").json()
    version_id = version["id"]
    assert (
        client.post(
            f"/api/v1/portfolios/{source_id}/versions/{version_id}/publish",
            json={
                "visibility": "public",
                "license": LICENSE_PUBLIC_FORK_ALLOWED,
                "provenance": "simulated",
                "consent_acknowledged": True,
                "disclosure_acknowledged": True,
            },
        ).status_code
        == 200
    )

    forked = client.post(
        f"/api/v1/portfolio-versions/{version_id}/fork",
        json={"name": "My fork"},
        headers={"Idempotency-Key": "fork-1"},
    )
    assert forked.status_code == 201
    fork_body = forked.json()
    assert fork_body["id"] != source_id
    assert fork_body["name"] == "My fork"
    assert fork_body["thesis"] == "Source thesis"
    assert fork_body["visibility"] == "private"
    assert fork_body["fork_lineage"] is not None
    assert fork_body["fork_lineage"]["source_portfolio_id"] == source_id
    assert fork_body["fork_lineage"]["source_version_id"] == version_id
    assert fork_body["fork_lineage"]["sync_enabled"] is False
    assert fork_body["fork_lineage"]["mirror_trades"] is False
    assert fork_body["wallet"]["id"] != source["wallet"]["id"]

    # Idempotent fork
    again = client.post(
        f"/api/v1/portfolio-versions/{version_id}/fork",
        json={"name": "Ignored"},
        headers={"Idempotency-Key": "fork-1"},
    )
    assert again.status_code == 201
    assert again.json()["id"] == fork_body["id"]

    # Independent: mutate source cash path does not change fork wallet id / lineage
    db = SessionLocal()
    fork_wallet = db.query(SimWallet).filter(SimWallet.portfolio_id == UUID(fork_body["id"])).one()
    source_wallet = db.query(SimWallet).filter(SimWallet.portfolio_id == UUID(source_id)).one()
    assert fork_wallet.id != source_wallet.id
    fork_positions = (
        db.query(SimPosition).filter(SimPosition.portfolio_id == UUID(fork_body["id"])).all()
    )
    assert any(p.symbol == "MSFT" for p in fork_positions)
    lots = (
        db.query(SimPositionLot).filter(SimPositionLot.portfolio_id == UUID(fork_body["id"])).all()
    )
    assert lots and all(lot.execution_id is None for lot in lots)
    assert (
        db.query(PortfolioFork)
        .filter(PortfolioFork.forked_portfolio_id == UUID(fork_body["id"]))
        .count()
        == 1
    )
    db.close()

    # Source remains private at portfolio level; published version is publicly readable.
    public_view = client.get(f"/api/v1/portfolio-versions/{version_id}")
    assert public_view.status_code == 200
    assert public_view.json()["fork_allowed"] is True

    # Independence: later source trades must not mutate the fork wallet/positions.
    fork_before = client.get(f"/api/v1/portfolios/{fork_body['id']}").json()
    fork_cash_before = fork_before["wallet"]["cash_balance"]
    source_preview = client.post(
        f"/api/v1/portfolios/{source_id}/orders/preview",
        json={"symbol": "MSFT", "side": "sell", "quantity": "1"},
    )
    assert source_preview.status_code == 200
    assert (
        client.post(
            f"/api/v1/portfolios/{source_id}/orders/confirm",
            json={"preview_id": source_preview.json()["preview_id"]},
            headers={"Idempotency-Key": "sell-msft-after-fork"},
        ).status_code
        == 200
    )
    fork_after = client.get(f"/api/v1/portfolios/{fork_body['id']}").json()
    assert fork_after["wallet"]["cash_balance"] == fork_cash_before
    assert fork_after["wallet"]["id"] == fork_before["wallet"]["id"]
    db = SessionLocal()
    fork_msft_qty = (
        db.query(SimPosition)
        .filter(
            SimPosition.portfolio_id == UUID(fork_body["id"]),
            SimPosition.symbol == "MSFT",
        )
        .one()
        .quantity
    )
    source_msft_qty = (
        db.query(SimPosition)
        .filter(
            SimPosition.portfolio_id == UUID(source_id),
            SimPosition.symbol == "MSFT",
        )
        .one()
        .quantity
    )
    assert money(fork_msft_qty) == money("2")
    assert money(source_msft_qty) == money("1")
    db.close()

    application.dependency_overrides.clear()
    refresh_settings()


def test_authz_denies_private_version_and_unforkable_license(db_engine, monkeypatch):
    application, client, SessionLocal = _client_for(db_engine, monkeypatch)
    _grant_creator(SessionLocal)

    portfolio_id = client.post("/api/v1/portfolios", json={"name": "Private"}).json()["id"]
    version_id = client.post(f"/api/v1/portfolios/{portfolio_id}/versions").json()["id"]

    # Draft private version is owner-visible via owned path.
    assert client.get(f"/api/v1/portfolios/{portfolio_id}/versions/{version_id}").status_code == 200

    # Publish as view_only — readable when public, but not forkable.
    assert (
        client.post(
            f"/api/v1/portfolios/{portfolio_id}/versions/{version_id}/publish",
            json={
                "visibility": "public",
                "license": LICENSE_VIEW_ONLY,
                "provenance": "simulated",
                "consent_acknowledged": True,
                "disclosure_acknowledged": True,
            },
        ).status_code
        == 200
    )
    denied_fork = client.post(f"/api/v1/portfolio-versions/{version_id}/fork", json={})
    assert denied_fork.status_code == 403

    # Foreign draft version inserted for another owner → 404 to current user.
    db = SessionLocal()
    other, _, _ = bootstrap_user_on_sign_in(db, entra_oid=f"other-{uuid4()}")
    foreign = Portfolio(
        owner_user_id=other.id,
        name="Foreign",
        visibility="private",
        provenance="simulated",
        status="active",
        currency_code="VUSD",
    )
    db.add(foreign)
    db.flush()
    foreign_version = PortfolioVersion(
        portfolio_id=foreign.id,
        owner_user_id=other.id,
        version_number=1,
        name="Foreign",
        holdings_json=[],
        allocation_json={"cash_balance": "1000.0000"},
        data_context_json={},
        checksum="a" * 64,
        status="draft",
        visibility="private",
        provenance="simulated",
    )
    db.add(foreign_version)
    db.commit()
    foreign_version_id = str(foreign_version.id)
    db.close()

    assert client.get(f"/api/v1/portfolio-versions/{foreign_version_id}").status_code == 404
    assert client.post(f"/api/v1/portfolio-versions/{foreign_version_id}/fork").status_code == 404

    application.dependency_overrides.clear()
    refresh_settings()


def test_versions_require_auth(db_engine, monkeypatch):
    application, client, _ = _client_for(db_engine, monkeypatch, app_env="production", dev_auth="false")
    assert client.get(f"/api/v1/portfolios/{uuid4()}/versions").status_code == 401
    assert client.post(f"/api/v1/portfolio-versions/{uuid4()}/fork").status_code == 401
    application.dependency_overrides.clear()
    refresh_settings()
