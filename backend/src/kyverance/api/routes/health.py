from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from kyverance.config import Settings, get_settings
from kyverance.db.session import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
def health(
    settings: Annotated[Settings, Depends(get_settings)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, str | bool]:
    db_status = "ok"
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        db_status = "error"
    return {
        "status": "ok" if db_status == "ok" else "degraded",
        "version": settings.app_version,
        "db": db_status,
    }


@router.get("/ready")
def ready(
    settings: Annotated[Settings, Depends(get_settings)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    checks: dict[str, Any] = {}
    try:
        db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:  # noqa: BLE001
        checks["database"] = f"error: {exc.__class__.__name__}"

    redis_status = "skipped"
    try:
        import redis

        client = redis.from_url(settings.redis_url, socket_connect_timeout=1)
        client.ping()
        redis_status = "ok"
    except Exception as exc:  # noqa: BLE001
        redis_status = f"error: {exc.__class__.__name__}"
    checks["redis"] = redis_status

    ok = checks.get("database") == "ok"
    return {"status": "ok" if ok else "degraded", "checks": checks}
