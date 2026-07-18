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

    checks["market_data_engine"] = "enabled" if settings.market_data_engine_enabled else "disabled"
    checks["market_data_jobs"] = "enabled" if settings.market_data_jobs_enabled else "disabled"
    checks["market_data_ingest_provider"] = settings.market_data_provider
    try:
        from kyverance.market_data.models import IngestionRun, LatestDailyPrice, MarketDataHealth

        latest_n = db.query(LatestDailyPrice).count()
        checks["market_data_latest_rows"] = latest_n
        last_pub = (
            db.query(IngestionRun)
            .filter(IngestionRun.status == "PUBLISHED")
            .order_by(IngestionRun.completed_at.desc())
            .first()
        )
        if last_pub and last_pub.completed_at:
            checks["market_data_last_publish"] = last_pub.completed_at.isoformat()
            checks["market_data_ingestion"] = "ok"
        else:
            checks["market_data_ingestion"] = "empty"
        for component in ("scheduler", "worker", "ingest"):
            health = db.get(MarketDataHealth, component)
            if health and health.last_success_at:
                checks[f"market_data_{component}_last_success"] = health.last_success_at.isoformat()
    except Exception as exc:  # noqa: BLE001
        checks["market_data_ingestion"] = f"error:{exc.__class__.__name__}"

    checks["research_engine"] = "enabled" if settings.research_engine_enabled else "disabled"
    checks["research_jobs"] = "enabled" if settings.research_jobs_enabled else "disabled"
    checks["research_ai"] = "enabled" if settings.research_ai_enabled else "disabled"
    try:
        from kyverance.research.models import ResearchHealth, SecurityResearchLatest

        checks["research_latest_pointers"] = db.query(SecurityResearchLatest).count()
        for component in ("scheduler", "worker"):
            health = db.get(ResearchHealth, component)
            if health and health.last_success_at:
                checks[f"research_{component}_last_success"] = health.last_success_at.isoformat()
    except Exception as exc:  # noqa: BLE001
        checks["research_status"] = f"error:{exc.__class__.__name__}"

    # Provider/AI outages must not fail readiness when Postgres is healthy.
    ok = checks.get("database") == "ok"
    return {"status": "ok" if ok else "degraded", "checks": checks}
