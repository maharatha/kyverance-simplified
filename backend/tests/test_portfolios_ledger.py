from __future__ import annotations

import os
from collections.abc import Generator
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("DEV_AUTH", "true")

from kyverance.audit.models import AuditEvent  # noqa: E402
from kyverance.config import refresh_settings  # noqa: E402
from kyverance.db.session import Base, get_db  # noqa: E402
from kyverance.identity.service import bootstrap_user_on_sign_in  # noqa: E402
from kyverance.main import create_app  # noqa: E402
from kyverance.portfolios.models import Portfolio  # noqa: E402
from kyverance.simulation.models import SimWallet, WalletLedgerEntry  # noqa: E402
from kyverance.simulation.money import money, money_str  # noqa: E402
from kyverance.portfolios.service import ledger_sum  # noqa: E402


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


def test_money_rejects_float_and_formats_string():
    with pytest.raises(TypeError):
        money(1.1)  # type: ignore[arg-type]
    assert money_str("1000") == "1000.0000"
    assert money_str(Decimal("1000.1")) == "1000.1000"


def test_portfolios_require_auth(db_engine, monkeypatch):
    application, client, _ = _client_for(db_engine, monkeypatch, app_env="production", dev_auth="false")
    assert client.get("/api/v1/portfolios").status_code == 401
    assert client.post("/api/v1/portfolios", json={"name": "A"}).status_code == 401
    application.dependency_overrides.clear()
    refresh_settings()


def test_create_list_read_multiple_isolated_portfolios(db_engine, monkeypatch):
    application, client, SessionLocal = _client_for(db_engine, monkeypatch)

    empty = client.get("/api/v1/portfolios")
    assert empty.status_code == 200
    assert empty.json()["empty_state"] == "empty"
    assert empty.json()["portfolios"] == []

    first = client.post(
        "/api/v1/portfolios",
        json={"name": "Core growth", "description": "Primary practice book"},
        headers={"Idempotency-Key": "create-core-1"},
    )
    assert first.status_code == 201
    first_body = first.json()
    assert first_body["name"] == "Core growth"
    assert first_body["visibility"] == "private"
    assert first_body["provenance"] == "simulated"
    assert first_body["cash_balance"] == "1000.0000"
    assert isinstance(first_body["cash_balance"], str)
    assert first_body["wallet"]["cash_balance"] == "1000.0000"
    assert first_body["wallet"]["complimentary_balance"] == "1000.0000"
    assert len(first_body["ledger"]) == 1
    assert first_body["ledger"][0]["amount"] == "1000.0000"
    assert first_body["ledger"][0]["source_type"] == "INITIAL_ALLOCATION"
    assert "." in first_body["ledger"][0]["amount"]
    # Ensure JSON did not coerce money to a number.
    assert '"' in first.text and "1000.0000" in first.text

    second = client.post(
        "/api/v1/portfolios",
        json={"name": "Income sleeve"},
        headers={"Idempotency-Key": "create-income-1"},
    )
    assert second.status_code == 201
    second_body = second.json()
    assert second_body["id"] != first_body["id"]
    assert second_body["wallet"]["id"] != first_body["wallet"]["id"]
    assert second_body["cash_balance"] == "1000.0000"

    listed = client.get("/api/v1/portfolios")
    assert listed.status_code == 200
    listed_body = listed.json()
    assert listed_body["empty_state"] == "populated"
    assert len(listed_body["portfolios"]) == 2
    assert all(isinstance(p["cash_balance"], str) for p in listed_body["portfolios"])

    detail = client.get(f"/api/v1/portfolios/{first_body['id']}")
    assert detail.status_code == 200
    assert detail.json()["id"] == first_body["id"]
    assert "Simulated portfolio" in detail.json()["simulation_notice"]

    db = SessionLocal()
    assert db.query(Portfolio).count() == 2
    assert db.query(SimWallet).count() == 2
    assert db.query(WalletLedgerEntry).count() == 2
    wallets = db.query(SimWallet).all()
    for wallet in wallets:
        assert ledger_sum(db, wallet.id) == money(wallet.balance)
        assert money(wallet.balance) == money("1000")
    audits = {e.action for e in db.query(AuditEvent).all()}
    assert "portfolio.create" in audits
    assert "wallet.ledger.append" in audits
    db.close()

    application.dependency_overrides.clear()
    refresh_settings()


def test_create_is_idempotent(db_engine, monkeypatch):
    application, client, SessionLocal = _client_for(db_engine, monkeypatch)

    payload = {"name": "Idempotent book"}
    headers = {"Idempotency-Key": "same-key-42"}
    first = client.post("/api/v1/portfolios", json=payload, headers=headers)
    second = client.post("/api/v1/portfolios", json={"name": "Different name ignored"}, headers=headers)
    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] == second.json()["id"]
    assert first.json()["name"] == "Idempotent book"
    assert second.json()["name"] == "Idempotent book"

    db = SessionLocal()
    assert db.query(Portfolio).count() == 1
    assert db.query(WalletLedgerEntry).count() == 1
    db.close()

    application.dependency_overrides.clear()
    refresh_settings()


def test_object_authorization_hides_other_users_portfolio(db_engine, monkeypatch):
    application, client, SessionLocal = _client_for(db_engine, monkeypatch)

    created = client.post("/api/v1/portfolios", json={"name": "Owner only"})
    assert created.status_code == 201
    portfolio_id = created.json()["id"]

    db = SessionLocal()
    other, _, _ = bootstrap_user_on_sign_in(
        db,
        entra_oid=f"other-user-{uuid4()}",
        email="other@example.com",
        display_name="Other User",
        actor_subject="other-user",
    )
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
    foreign_wallet = SimWallet(
        portfolio_id=foreign.id,
        owner_user_id=other.id,
        currency_code="VUSD",
        balance=money("500"),
        complimentary_balance=money("500"),
        version=1,
    )
    db.add(foreign_wallet)
    db.commit()
    foreign_id = str(foreign.id)
    db.close()

    # Dev auth always resolves to the same bootstrap user — foreign portfolio must 404.
    missing = client.get(f"/api/v1/portfolios/{foreign_id}")
    assert missing.status_code == 404
    assert missing.json()["detail"] == "Portfolio not found"

    # Owner portfolio remains readable.
    assert client.get(f"/api/v1/portfolios/{portfolio_id}").status_code == 200

    listed = client.get("/api/v1/portfolios").json()["portfolios"]
    assert all(p["id"] != foreign_id for p in listed)
    assert any(p["id"] == portfolio_id for p in listed)

    application.dependency_overrides.clear()
    refresh_settings()


def test_unknown_portfolio_is_404(db_engine, monkeypatch):
    application, client, _ = _client_for(db_engine, monkeypatch)
    response = client.get(f"/api/v1/portfolios/{uuid4()}")
    assert response.status_code == 404
    application.dependency_overrides.clear()
    refresh_settings()
