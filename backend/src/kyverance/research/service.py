"""Research read service — serves published versions only; cold miss enqueues rebuild."""

from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy.orm import Session

from kyverance.config import Settings, get_settings
from kyverance.research.cache import get_research_cache, redis_keys, version_key
from kyverance.research.constants import (
    FRESHNESS_REVALIDATING,
    JOB_COLD_ON_DEMAND,
    PUB_STATUS_PUBLISHED,
)
from kyverance.research.jobs.queue import enqueue_job
from kyverance.research.models import ResearchSecurity
from kyverance.research.persist import latest_version, load_recoverable_report

logger = logging.getLogger(__name__)


def resolve_security(db: Session, symbol: str) -> ResearchSecurity | None:
    sym = symbol.upper().replace(".US", "")
    return (
        db.query(ResearchSecurity)
        .filter(ResearchSecurity.ticker == sym, ResearchSecurity.status == "active")
        .order_by(ResearchSecurity.created_at.asc())
        .first()
    )


def _freshness_from_version(version, report: dict[str, Any] | None = None) -> dict[str, Any]:
    stale = version.freshness_status in {"STALE", "REVALIDATING", "FAILED_REFRESH"}
    data_mode = "end_of_day"
    if report:
        data_mode = str(report.get("data_mode") or report.get("dataMode") or data_mode)
    elif isinstance(version.report_payload, dict):
        data_mode = str(
            version.report_payload.get("data_mode")
            or version.report_payload.get("dataMode")
            or data_mode
        )
    return {
        "researchVersion": str(version.id),
        "marketDate": version.market_date,
        "generatedAt": version.generated_at.isoformat() if version.generated_at else None,
        "publishedAt": version.published_at.isoformat() if version.published_at else None,
        "freshnessStatus": version.freshness_status,
        "sourceDataTimestamp": version.source_data_timestamp.isoformat()
        if version.source_data_timestamp
        else None,
        "nextExpectedRefresh": version.next_expected_refresh.isoformat()
        if version.next_expected_refresh
        else None,
        "isStale": stale or version.freshness_status == "STALE",
        "revalidationInProgress": version.freshness_status == "REVALIDATING",
        "dataMode": data_mode,
        "publicationStatus": version.publication_status,
    }


def get_research_for_symbol(
    db: Session,
    symbol: str,
    *,
    settings: Settings | None = None,
    enqueue_if_missing: bool = True,
    exchange: str = "XNAS",
) -> tuple[dict[str, Any] | None, int]:
    """
    Cache-first research fetch with Postgres published verification.
    Returns (payload, http_status_hint). Handlers must not perform deep generation.
    """
    settings = settings or get_settings()
    if not settings.research_engine_enabled:
        return {
            "symbol": symbol.upper(),
            "freshnessStatus": "UNAVAILABLE",
            "isStale": True,
            "revalidationInProgress": False,
            "message": "Research engine disabled",
            "servedFrom": "none",
        }, 503

    security = resolve_security(db, symbol)
    if security is None:
        if enqueue_if_missing and settings.research_jobs_enabled:
            enqueue_job(
                db,
                job_type=JOB_COLD_ON_DEMAND,
                idempotency_key=f"cold:{symbol.upper()}:bootstrap",
                payload={"ticker": symbol.upper().replace(".US", ""), "exchange": exchange.upper()},
            )
            return {
                "symbol": symbol.upper().replace(".US", ""),
                "freshnessStatus": FRESHNESS_REVALIDATING,
                "isStale": True,
                "revalidationInProgress": True,
                "dataMode": "end_of_day",
                "message": "Research generation enqueued",
                "servedFrom": "none",
            }, 202
        return None, 404

    cache = get_research_cache(settings)
    keys = redis_keys(str(security.id))
    latest_id = cache.get(keys["latest"]) if cache.available() else None
    published = latest_version(db, security.id)

    if latest_id and published and str(published.id) == str(latest_id):
        raw = cache.get(version_key(str(security.id), latest_id))
        if raw:
            try:
                data = json.loads(raw)
                if published.publication_status != PUB_STATUS_PUBLISHED:
                    raise ValueError("cache_unpublished")
                data["servedFrom"] = "cache"
                data.setdefault("symbol", security.ticker)
                data.setdefault("securityId", str(security.id))
                data["publicationStatus"] = published.publication_status
                return data, 200
            except (json.JSONDecodeError, ValueError):
                logger.info("research.cache.mismatch security=%s", security.ticker)

    version = published
    if not version:
        if enqueue_if_missing and settings.research_jobs_enabled:
            enqueue_job(
                db,
                job_type=JOB_COLD_ON_DEMAND,
                idempotency_key=f"cold:{security.id}:{security.ticker}",
                security_id=security.id,
                payload={"ticker": security.ticker, "exchange": security.exchange},
            )
            return {
                "symbol": security.ticker,
                "securityId": str(security.id),
                "freshnessStatus": FRESHNESS_REVALIDATING,
                "isStale": True,
                "revalidationInProgress": True,
                "dataMode": "end_of_day",
                "message": "Research generation enqueued",
                "servedFrom": "none",
            }, 202
        return None, 404

    report = load_recoverable_report(db, settings, version)
    freshness = _freshness_from_version(version, report)
    if report is None:
        return {
            "symbol": security.ticker,
            "securityId": str(security.id),
            "executiveSummary": version.executive_summary,
            "servedFrom": "postgres",
            **freshness,
        }, 200

    payload = {
        **report,
        **freshness,
        "symbol": security.ticker,
        "securityId": str(security.id),
        "researchVersion": str(version.id),
        "servedFrom": "postgres",
    }
    return payload, 200


def get_published_research_ref(db: Session, symbol: str) -> dict[str, str] | None:
    """Authorized canonical research reference for AGENT-01 facts packets."""
    security = resolve_security(db, symbol)
    if not security:
        return None
    version = latest_version(db, security.id)
    if not version or version.publication_status != PUB_STATUS_PUBLISHED:
        return None
    return {
        "kind": "canonical_research",
        "ref": str(version.id),
        "label": (
            f"{security.ticker} research {version.market_date} "
            f"checksum {version.evidence_hash[:12]}"
        ),
        "security_id": str(security.id),
        "ticker": security.ticker,
        "evidence_hash": version.evidence_hash,
        "publication_status": version.publication_status,
    }
