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
os.environ.setdefault("QUOTE_MODE", "fixture")

from kyverance.audit.models import AuditEvent  # noqa: E402
from kyverance.config import refresh_settings  # noqa: E402
from kyverance.db.session import Base, get_db  # noqa: E402
from kyverance.identity.service import bootstrap_user_on_sign_in  # noqa: E402
from kyverance.main import create_app  # noqa: E402
from kyverance.portfolios.models import Portfolio  # noqa: E402
from kyverance.portfolios.service import ledger_sum  # noqa: E402
from kyverance.simulation.models import (  # noqa: E402
    OrderPreview,
    OrderReceipt,
    SimExecution,
    SimOrder,
    SimPosition,
    SimWallet,
    WalletLedgerEntry,
)
from kyverance.simulation.money import money, money_str, qty  # noqa: E402


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


def _client_for(db_engine, monkeypatch):
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DEV_AUTH", "true")
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


def _create_portfolio(client, name: str = "Book", key: str | None = None):
    headers = {"Idempotency-Key": key} if key else {}
    res = client.post("/api/v1/portfolios", json={"name": name}, headers=headers)
    assert res.status_code == 201, res.text
    return res.json()


def test_money_qty_reject_float():
    with pytest.raises(TypeError):
        money(1.1)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        qty(1.1)  # type: ignore[arg-type]


def test_preview_buy_and_confirm_updates_ledger_and_position(db_engine, monkeypatch):
    application, client, SessionLocal = _client_for(db_engine, monkeypatch)
    portfolio = _create_portfolio(client, key="ord-create-1")
    pid = portfolio["id"]

    preview = client.post(
        f"/api/v1/portfolios/{pid}/orders/preview",
        json={"symbol": "AAPL", "side": "buy", "quantity": "1"},
    )
    assert preview.status_code == 200, preview.text
    body = preview.json()
    assert body["symbol"] == "AAPL"
    assert body["side"] == "buy"
    assert isinstance(body["quantity"], str)
    assert isinstance(body["notional"], str)
    assert body["quote"]["data_mode"] == "fixture"
    assert body["quote"]["freshness_label"] == "fresh"
    assert body["quote"]["execution_policy"] == "market_us_equity_simulated"
    assert "Simulated order only" in body["disclosure"]
    preview_id = body["preview_id"]

    confirm = client.post(
        f"/api/v1/portfolios/{pid}/orders/confirm",
        json={"preview_id": preview_id},
        headers={"Idempotency-Key": "confirm-aapl-1"},
    )
    assert confirm.status_code == 200, confirm.text
    receipt = confirm.json()
    assert receipt["status"] == "EXECUTED"
    assert isinstance(receipt["execution_price"], str)
    assert isinstance(receipt["cash_balance"], str)
    assert len(receipt["ledger_entry_ids"]) >= 1
    assert receipt["quote"]["data_mode"] == "fixture"

    # Idempotent replay
    replay = client.post(
        f"/api/v1/portfolios/{pid}/orders/confirm",
        json={"preview_id": preview_id},
        headers={"Idempotency-Key": "confirm-aapl-1"},
    )
    assert replay.status_code == 200
    assert replay.json()["order_id"] == receipt["order_id"]
    assert replay.json()["receipt_id"] == receipt["receipt_id"]

    detail = client.get(f"/api/v1/portfolios/{pid}")
    assert detail.status_code == 200
    cash = money(detail.json()["cash_balance"])
    assert cash < money("1000")
    assert cash == money(receipt["cash_balance"])

    positions = client.get(f"/api/v1/portfolios/{pid}/positions")
    assert positions.status_code == 200
    assert len(positions.json()["positions"]) == 1
    assert positions.json()["positions"][0]["symbol"] == "AAPL"
    assert positions.json()["positions"][0]["quantity"] == "1.0000000000"

    activity = client.get(f"/api/v1/portfolios/{pid}/activity")
    assert activity.status_code == 200
    assert len(activity.json()["items"]) == 1

    recon = client.get(f"/api/v1/portfolios/{pid}/reconciliation")
    assert recon.status_code == 200
    assert recon.json()["ok"] is True

    db = SessionLocal()
    assert db.query(SimOrder).count() == 1
    assert db.query(SimExecution).count() == 1
    assert db.query(OrderReceipt).count() == 1
    assert db.query(SimPosition).count() == 1
    wallet = db.query(SimWallet).one()
    assert ledger_sum(db, wallet.id) == money(wallet.balance)
    audits = {e.action for e in db.query(AuditEvent).all()}
    assert "order.preview" in audits
    assert "order.confirm" in audits
    db.close()

    application.dependency_overrides.clear()
    refresh_settings()


def test_confirm_requires_idempotency_and_preview_binding(db_engine, monkeypatch):
    application, client, _ = _client_for(db_engine, monkeypatch)
    portfolio = _create_portfolio(client, key="ord-create-2")
    pid = portfolio["id"]
    preview = client.post(
        f"/api/v1/portfolios/{pid}/orders/preview",
        json={"symbol": "MSFT", "side": "buy", "notional": "100.0000"},
    ).json()

    missing = client.post(
        f"/api/v1/portfolios/{pid}/orders/confirm",
        json={"preview_id": preview["preview_id"]},
    )
    assert missing.status_code == 400
    assert "Idempotency-Key" in missing.json()["detail"]

    # Confirm once
    first = client.post(
        f"/api/v1/portfolios/{pid}/orders/confirm",
        json={"preview_id": preview["preview_id"]},
        headers={"Idempotency-Key": "confirm-msft-1"},
    )
    assert first.status_code == 200

    # Same key, different preview → conflict
    other_preview = client.post(
        f"/api/v1/portfolios/{pid}/orders/preview",
        json={"symbol": "MSFT", "side": "buy", "notional": "50.0000"},
    ).json()
    conflict = client.post(
        f"/api/v1/portfolios/{pid}/orders/confirm",
        json={"preview_id": other_preview["preview_id"]},
        headers={"Idempotency-Key": "confirm-msft-1"},
    )
    assert conflict.status_code == 409

    # Consumed preview cannot be reused
    reused = client.post(
        f"/api/v1/portfolios/{pid}/orders/confirm",
        json={"preview_id": preview["preview_id"]},
        headers={"Idempotency-Key": "confirm-msft-2"},
    )
    assert reused.status_code == 409

    application.dependency_overrides.clear()
    refresh_settings()


def test_insufficient_cash_and_oversell_leave_no_partial_write(db_engine, monkeypatch):
    application, client, SessionLocal = _client_for(db_engine, monkeypatch)
    portfolio = _create_portfolio(client, key="ord-create-3")
    pid = portfolio["id"]

    overbuy = client.post(
        f"/api/v1/portfolios/{pid}/orders/preview",
        json={"symbol": "AAPL", "side": "buy", "notional": "5000.0000"},
    )
    assert overbuy.status_code == 400
    assert "Insufficient buying power" in overbuy.json()["detail"]

    sell = client.post(
        f"/api/v1/portfolios/{pid}/orders/preview",
        json={"symbol": "AAPL", "side": "sell", "quantity": "1"},
    )
    assert sell.status_code == 400

    # Successful buy then oversell
    preview = client.post(
        f"/api/v1/portfolios/{pid}/orders/preview",
        json={"symbol": "AAPL", "side": "buy", "quantity": "2"},
    ).json()
    client.post(
        f"/api/v1/portfolios/{pid}/orders/confirm",
        json={"preview_id": preview["preview_id"]},
        headers={"Idempotency-Key": "buy-two-shares"},
    )
    oversell = client.post(
        f"/api/v1/portfolios/{pid}/orders/preview",
        json={"symbol": "AAPL", "side": "sell", "quantity": "3"},
    )
    assert oversell.status_code == 400
    assert "Insufficient holdings" in oversell.json()["detail"]

    db = SessionLocal()
    assert db.query(SimOrder).count() == 1
    assert db.query(WalletLedgerEntry).count() == 2  # initial + buy debit
    assert money(db.query(SimPosition).one().quantity) == qty("2")
    db.close()

    application.dependency_overrides.clear()
    refresh_settings()


def test_object_authorization_on_orders(db_engine, monkeypatch):
    application, client, SessionLocal = _client_for(db_engine, monkeypatch)
    portfolio = _create_portfolio(client, key="ord-create-4")
    pid = portfolio["id"]

    db = SessionLocal()
    other, _, _ = bootstrap_user_on_sign_in(
        db,
        entra_oid=f"other-{uuid4()}",
        email="other@example.com",
        display_name="Other",
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
    foreign_id = str(foreign.id)
    db.commit()
    db.close()

    denied = client.post(
        f"/api/v1/portfolios/{foreign_id}/orders/preview",
        json={"symbol": "AAPL", "side": "buy", "quantity": "1"},
    )
    assert denied.status_code == 404

    denied_activity = client.get(f"/api/v1/portfolios/{foreign_id}/activity")
    assert denied_activity.status_code == 404

    # Own portfolio still works
    ok = client.post(
        f"/api/v1/portfolios/{pid}/orders/preview",
        json={"symbol": "SPY", "side": "buy", "quantity": "1"},
    )
    assert ok.status_code == 200

    application.dependency_overrides.clear()
    refresh_settings()


def test_unsupported_symbol_and_xor_quantity(db_engine, monkeypatch):
    application, client, _ = _client_for(db_engine, monkeypatch)
    portfolio = _create_portfolio(client, key="ord-create-5")
    pid = portfolio["id"]

    both = client.post(
        f"/api/v1/portfolios/{pid}/orders/preview",
        json={"symbol": "AAPL", "side": "buy", "quantity": "1", "notional": "10"},
    )
    assert both.status_code == 422

    bad = client.post(
        f"/api/v1/portfolios/{pid}/orders/preview",
        json={"symbol": "ZZZZ", "side": "buy", "quantity": "1"},
    )
    assert bad.status_code == 400
    assert "Unsupported symbol" in bad.json()["detail"]

    application.dependency_overrides.clear()
    refresh_settings()


def test_sell_round_trip_and_decimal_strings(db_engine, monkeypatch):
    application, client, SessionLocal = _client_for(db_engine, monkeypatch)
    portfolio = _create_portfolio(client, key="ord-create-6")
    pid = portfolio["id"]

    buy_preview = client.post(
        f"/api/v1/portfolios/{pid}/orders/preview",
        json={"symbol": "QQQ", "side": "buy", "quantity": "1"},
    ).json()
    buy = client.post(
        f"/api/v1/portfolios/{pid}/orders/confirm",
        json={"preview_id": buy_preview["preview_id"]},
        headers={"Idempotency-Key": "buy-qqq-one"},
    ).json()
    assert '"' in client.get(f"/api/v1/portfolios/{pid}").text

    sell_preview = client.post(
        f"/api/v1/portfolios/{pid}/orders/preview",
        json={"symbol": "QQQ", "side": "sell", "quantity": "1"},
    ).json()
    sell = client.post(
        f"/api/v1/portfolios/{pid}/orders/confirm",
        json={"preview_id": sell_preview["preview_id"]},
        headers={"Idempotency-Key": "sell-qqq-one"},
    ).json()
    assert sell["status"] == "EXECUTED"
    assert sell["position_quantity"] == "0.0000000000"

    positions = client.get(f"/api/v1/portfolios/{pid}/positions").json()
    assert positions["positions"] == []

    db = SessionLocal()
    wallet = db.query(SimWallet).one()
    # Cash near starting allocation (buy/sell with slippage leaves a small gap).
    assert ledger_sum(db, wallet.id) == money(wallet.balance)
    assert money(wallet.balance) < money("1000")
    assert money(wallet.balance) > money("990")
    assert db.query(OrderPreview).count() == 2
    db.close()

    application.dependency_overrides.clear()
    refresh_settings()
