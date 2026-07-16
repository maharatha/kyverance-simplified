from __future__ import annotations

import os

import pytest
from sqlalchemy import create_engine, text


@pytest.mark.skipif(
    os.environ.get("DATABASE_URL") is None,
    reason="DATABASE_URL not set",
)
def test_postgres_connectivity():
    engine = create_engine(os.environ["DATABASE_URL"], pool_pre_ping=True)
    with engine.connect() as conn:
        assert conn.execute(text("SELECT 1")).scalar() == 1


@pytest.mark.skipif(
    os.environ.get("REDIS_URL") is None,
    reason="REDIS_URL not set",
)
def test_redis_connectivity():
    import redis

    client = redis.from_url(os.environ["REDIS_URL"], socket_connect_timeout=2)
    assert client.ping() is True
