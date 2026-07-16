from __future__ import annotations

from fastapi.testclient import TestClient

from kyverance.main import create_app


def test_health_endpoint_returns_payload():
    client = TestClient(create_app())
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert "status" in body
    assert "version" in body
    assert "db" in body


def test_settings_defaults():
    from kyverance.config import Settings

    settings = Settings(
        database_url="postgresql+psycopg://kyverance:kyverance@localhost:5432/kyverance_test",
        redis_url="redis://localhost:6379/0",
    )
    assert settings.app_name.startswith("Kyverance")
    assert "localhost:3000" in settings.cors_origin_list[0]
