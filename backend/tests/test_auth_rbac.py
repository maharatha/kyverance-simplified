from __future__ import annotations

import os
from collections.abc import Generator
from typing import Annotated

import pytest
from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("DEV_AUTH", "true")

from kyverance.audit.models import AuditEvent  # noqa: E402
from kyverance.auth.authorize import require_role  # noqa: E402
from kyverance.auth.models import AuthenticatedSubject  # noqa: E402
from kyverance.config import Settings, refresh_settings  # noqa: E402
from kyverance.db.session import Base, get_db  # noqa: E402
from kyverance.identity.models import ConsentRecord, RoleGrant, User  # noqa: E402
from kyverance.identity.roles import RoleKey  # noqa: E402
from kyverance.identity.service import bootstrap_user_on_sign_in, grant_role, record_consent  # noqa: E402
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


def test_development_identity_disabled_outside_local_test():
    settings = Settings(dev_auth=True, app_env="production")
    assert settings.development_identity_enabled is False

    settings = Settings(dev_auth=True, app_env="local")
    assert settings.development_identity_enabled is True


def test_me_requires_auth_when_dev_disabled(db_engine, monkeypatch):
    application, client, _ = _client_for(db_engine, monkeypatch, app_env="production", dev_auth="false")
    response = client.get("/api/v1/me")
    assert response.status_code == 401
    assert response.json()["detail"] == "Authentication required"
    application.dependency_overrides.clear()
    refresh_settings()


def test_me_development_identity_bootstraps_member(db_engine, monkeypatch):
    application, client, SessionLocal = _client_for(db_engine, monkeypatch)

    first = client.get("/api/v1/me")
    assert first.status_code == 200
    body = first.json()
    assert body["subject"] == "dev-user-001"
    assert body["is_dev"] is True
    assert body["roles"] == ["member"]
    assert body["user_id"]

    second = client.get("/api/v1/me")
    assert second.status_code == 200
    assert second.json()["user_id"] == body["user_id"]
    assert second.json()["roles"] == ["member"]

    db = SessionLocal()
    users = db.query(User).all()
    grants = db.query(RoleGrant).all()
    audits = db.query(AuditEvent).all()
    assert len(users) == 1
    assert len(grants) == 1
    assert grants[0].role_key == "member"
    assert any(event.action == "user.bootstrap" for event in audits)
    assert any(event.action == "role_grant.create" for event in audits)
    db.close()

    application.dependency_overrides.clear()


def test_bootstrap_idempotent_under_retry(db_session: Session):
    user_a, roles_a, created_a = bootstrap_user_on_sign_in(
        db_session,
        entra_oid="oid-repeat-001",
        given_name="Ada",
        family_name="Lovelace",
    )
    assert created_a is True
    assert roles_a == frozenset({"member"})

    user_b, roles_b, created_b = bootstrap_user_on_sign_in(
        db_session,
        entra_oid="oid-repeat-001",
        given_name="Ada",
        family_name="Lovelace",
    )
    assert created_b is False
    assert user_b.id == user_a.id
    assert roles_b == frozenset({"member"})
    assert db_session.query(User).count() == 1
    assert db_session.query(RoleGrant).count() == 1


def test_invalid_bearer_returns_401(db_engine, monkeypatch):
    application, client, _ = _client_for(
        db_engine,
        monkeypatch,
        app_env="test",
        dev_auth="false",
        ENTRA_AUDIENCE="api://kyverance-api",
        ENTRA_ISSUER="https://example.ciamlogin.com/tenant/v2.0",
        ENTRA_JWKS_URL="https://example.invalid/keys",
    )
    response = client.get("/api/v1/me", headers={"Authorization": "Bearer not-a-jwt"})
    assert response.status_code == 401
    application.dependency_overrides.clear()
    refresh_settings()


def test_require_role_denies_without_role(db_engine, monkeypatch):
    application, client, _ = _client_for(db_engine, monkeypatch)

    @application.get("/api/v1/moderator-only")
    def moderator_only(
        subject: Annotated[AuthenticatedSubject, Depends(require_role(RoleKey.MODERATOR))],
    ):
        return {"ok": True, "subject": subject.subject}

    response = client.get("/api/v1/moderator-only")
    assert response.status_code == 403
    assert response.json()["detail"] == "Insufficient role"
    application.dependency_overrides.clear()


def test_grant_role_and_consent_emit_audit(db_session: Session):
    user, _roles, _ = bootstrap_user_on_sign_in(db_session, entra_oid="oid-audit-001")
    grant_role(db_session, user=user, role_key=RoleKey.CREATOR.value, actor_subject="admin-001")
    record_consent(
        db_session,
        user=user,
        consent_type="terms_of_service",
        granted=True,
        actor_subject="oid-audit-001",
    )

    actions = {event.action for event in db_session.query(AuditEvent).all()}
    assert "role_grant.create" in actions
    assert "consent.create" in actions
    assert db_session.query(ConsentRecord).count() == 1


def test_client_header_cannot_enable_dev_auth(db_engine, monkeypatch):
    application, client, _ = _client_for(db_engine, monkeypatch, app_env="production", dev_auth="false")
    response = client.get(
        "/api/v1/me",
        headers={"X-Dev-Auth": "true", "X-Enable-Dev-Auth": "1"},
    )
    assert response.status_code == 401
    application.dependency_overrides.clear()
    refresh_settings()
