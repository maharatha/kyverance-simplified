from __future__ import annotations

import os
from collections.abc import Generator
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
from kyverance.connectors.models import (  # noqa: E402
    PlaidAccount,
    PlaidConnection,
    PlaidDeletionRequest,
    PlaidHolding,
)
from kyverance.connectors.token_crypto import decrypt_access_token, encrypt_access_token  # noqa: E402
from kyverance.db.session import Base, get_db  # noqa: E402
from kyverance.identity.models import ConsentRecord, User  # noqa: E402
from kyverance.identity.service import bootstrap_user_on_sign_in  # noqa: E402
from kyverance.main import create_app  # noqa: E402


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


def _client_for(db_engine, monkeypatch, *, app_env: str = "test", dev_auth: str = "true", **extra_env):
    monkeypatch.setenv("APP_ENV", app_env)
    monkeypatch.setenv("DEV_AUTH", dev_auth)
    for key, value in extra_env.items():
        monkeypatch.setenv(key, value)
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


def _assert_no_secrets(payload: dict | list) -> None:
    blob = str(payload).lower()
    assert "access_token" not in blob
    assert "access_token_ciphertext" not in blob
    assert "access-sandbox-fake" not in blob
    assert "ciphertext" not in blob


def test_connectors_require_auth(db_engine, monkeypatch):
    application, client, _ = _client_for(db_engine, monkeypatch, app_env="production", dev_auth="false")
    response = client.get("/api/v1/connectors")
    assert response.status_code == 401
    application.dependency_overrides.clear()
    refresh_settings()


def test_fake_provider_consent_exchange_disconnect_deletion(db_engine, monkeypatch):
    application, client, SessionLocal = _client_for(db_engine, monkeypatch)

    overview = client.get("/api/v1/connectors")
    assert overview.status_code == 200
    body = overview.json()
    assert body["mode"] == "fake"
    assert body["configured"] is True
    assert body["plaid_configured"] is False
    assert body["empty_state"] == "consent_required"
    assert body["connections"] == []
    _assert_no_secrets(body)

    denied = client.post("/api/v1/connectors/plaid/link-token")
    assert denied.status_code == 403

    consent = client.post("/api/v1/connectors/plaid/consent", json={"granted": True})
    assert consent.status_code == 200
    assert consent.json()["connect_consent_granted"] is True
    assert consent.json()["empty_state"] == "ready_fake"

    linked = client.post("/api/v1/connectors/plaid/fake-connect")
    assert linked.status_code == 200
    linked_body = linked.json()
    assert linked_body["empty_state"] == "populated"
    assert len(linked_body["connections"]) == 1
    connection = linked_body["connections"][0]
    assert connection["status"] == "connected"
    assert connection["institution_name"]
    assert len(connection["accounts"]) == 2
    assert connection["accounts"][0]["provenance"] == "plaid_read_only"
    assert connection["accounts"][0]["source_label"] == "Linked account (read-only)"
    assert any(h["symbol"] == "VOO" for acct in connection["accounts"] for h in acct["holdings"])
    _assert_no_secrets(linked_body)
    connection_id = connection["id"]

    db = SessionLocal()
    stored = db.query(PlaidConnection).one()
    assert stored.access_token_ciphertext
    assert stored.encryption_kid
    assert "access-sandbox-fake" not in (stored.access_token_ciphertext or "")
    plaintext = decrypt_access_token(stored.access_token_ciphertext, refresh_settings())
    assert plaintext.startswith("access-sandbox-fake-")
    audits = [e.action for e in db.query(AuditEvent).all()]
    assert "plaid.connection.create" in audits
    assert "consent.create" in audits or "consent.update" in audits
    assert db.query(PlaidAccount).count() == 2
    assert db.query(PlaidHolding).count() == 2
    db.close()

    refreshed = client.post(f"/api/v1/connectors/connections/{connection_id}/refresh")
    assert refreshed.status_code == 200
    assert refreshed.json()["connections"][0]["status"] == "connected"

    disconnected = client.delete(f"/api/v1/connectors/connections/{connection_id}")
    assert disconnected.status_code == 200
    disc = disconnected.json()["connections"][0]
    assert disc["status"] == "disconnected"
    assert disc["disconnected_at"]

    db = SessionLocal()
    stored = db.query(PlaidConnection).one()
    assert stored.access_token_ciphertext is None
    assert any(e.action == "plaid.connection.disconnect" for e in db.query(AuditEvent).all())
    db.close()

    # Reconnect then request deletion (purges mirrored rows).
    client.post("/api/v1/connectors/plaid/consent", json={"granted": True})
    reconnected = client.post("/api/v1/connectors/plaid/fake-connect")
    connection_id = reconnected.json()["connections"][0]["id"]
    deleted = client.post(f"/api/v1/connectors/connections/{connection_id}/deletion-request")
    assert deleted.status_code == 200
    assert deleted.json()["status"] == "completed"

    db = SessionLocal()
    stored = db.query(PlaidConnection).one()
    assert stored.status == "pending_deletion"
    assert stored.access_token_ciphertext is None
    assert db.query(PlaidAccount).count() == 0
    assert db.query(PlaidHolding).count() == 0
    assert db.query(PlaidDeletionRequest).count() == 1
    retention = (
        db.query(ConsentRecord)
        .filter(ConsentRecord.consent_type == "plaid.data_retention")
        .one()
    )
    assert retention.granted is False
    assert any(e.action == "plaid.connection.delete_request" for e in db.query(AuditEvent).all())
    db.close()

    application.dependency_overrides.clear()


def test_object_level_authorization_blocks_other_owner(db_engine, monkeypatch):
    application, client, SessionLocal = _client_for(db_engine, monkeypatch)

    client.post("/api/v1/connectors/plaid/consent", json={"granted": True})
    created = client.post("/api/v1/connectors/plaid/fake-connect")
    connection_id = created.json()["connections"][0]["id"]

    db = SessionLocal()
    other, _roles, _created = bootstrap_user_on_sign_in(db, entra_oid="other-owner-oid")
    victim = db.query(PlaidConnection).one()
    victim.user_id = other.id
    for account in db.query(PlaidAccount).all():
        account.user_id = other.id
    for holding in db.query(PlaidHolding).all():
        holding.user_id = other.id
    db.commit()
    db.close()

    assert client.delete(f"/api/v1/connectors/connections/{connection_id}").status_code == 404
    assert client.post(f"/api/v1/connectors/connections/{connection_id}/refresh").status_code == 404
    assert (
        client.post(f"/api/v1/connectors/connections/{connection_id}/deletion-request").status_code
        == 404
    )
    overview = client.get("/api/v1/connectors").json()
    assert overview["connections"] == []

    application.dependency_overrides.clear()


def test_exchange_rejects_without_consent(db_engine, monkeypatch):
    application, client, _ = _client_for(db_engine, monkeypatch)
    response = client.post(
        "/api/v1/connectors/plaid/exchange",
        json={"public_token": "public-fake-no-consent", "provider_key": "any"},
    )
    assert response.status_code == 403
    application.dependency_overrides.clear()


def test_unknown_connection_returns_404(db_engine, monkeypatch):
    application, client, _ = _client_for(db_engine, monkeypatch)
    client.post("/api/v1/connectors/plaid/consent", json={"granted": True})
    missing = uuid4()
    assert client.delete(f"/api/v1/connectors/connections/{missing}").status_code == 404
    application.dependency_overrides.clear()


def test_token_crypto_round_trip(db_session: Session, monkeypatch):
    monkeypatch.setenv("APP_ENV", "test")
    settings = refresh_settings()
    ciphertext, kid = encrypt_access_token("access-sandbox-fake-demo", settings)
    assert kid
    assert "access-sandbox-fake-demo" not in ciphertext
    assert decrypt_access_token(ciphertext, settings) == "access-sandbox-fake-demo"


def test_link_token_then_manual_exchange(db_engine, monkeypatch):
    application, client, _ = _client_for(db_engine, monkeypatch)
    client.post("/api/v1/connectors/plaid/consent", json={"granted": True})
    link = client.post("/api/v1/connectors/plaid/link-token")
    assert link.status_code == 200
    assert link.json()["mode"] == "fake"
    assert link.json()["link_token"].startswith("link-sandbox-fake-")

    exchanged = client.post(
        "/api/v1/connectors/plaid/exchange",
        json={"public_token": "public-sandbox-fake-manual", "provider_key": "any"},
    )
    assert exchanged.status_code == 200
    assert len(exchanged.json()["connections"]) == 1
    _assert_no_secrets(exchanged.json())
    application.dependency_overrides.clear()
