"""Research pipeline: evidence → generate → validate → persist → publish."""

from __future__ import annotations

import logging
from datetime import date
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from kyverance.config import Settings, get_settings
from kyverance.research.cache import (
    acquire_generation_lock,
    get_research_cache,
    publish_research_atomic,
    release_generation_lock,
)
from kyverance.research.constants import (
    FRESHNESS_CURRENT,
    JOB_CACHE_REPAIR,
    PUB_STATUS_PUBLISHED,
    TIER_ACTIVE,
)
from kyverance.research.evidence import EvidenceNotReady, collect_internal_evidence
from kyverance.research.generate import generate_canonical_report
from kyverance.research.material_change import evaluate_material_change
from kyverance.research.persist import (
    find_published_by_evidence,
    get_or_create_security,
    latest_version,
    load_recoverable_report,
    mark_artifact_failed,
    mark_artifact_ready,
    mark_published,
    persist_assessment,
    persist_immutable_version,
    write_version_artifacts,
)
from kyverance.research.validate import ResearchValidationError, assert_valid

logger = logging.getLogger(__name__)


def _freshness_payload(version, report: dict[str, Any] | None = None) -> dict[str, Any]:
    data_mode = "end_of_day"
    if report:
        data_mode = str(report.get("data_mode") or report.get("dataMode") or data_mode)
    elif isinstance(version.report_payload, dict):
        data_mode = str(
            version.report_payload.get("data_mode")
            or version.report_payload.get("dataMode")
            or data_mode
        )
    stale = version.freshness_status in {"STALE", "REVALIDATING", "FAILED_REFRESH"}
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


def _try_publish_cache(db: Session, settings: Settings, security_id: str, version, report: dict[str, Any]) -> bool:
    try:
        cache = get_research_cache(settings)
        freshness = _freshness_payload(version, report)
        publish_research_atomic(
            cache,
            security_id=security_id,
            version_id=str(version.id),
            report={**report, **freshness, "servedFrom": "cache"},
            freshness=freshness,
        )
        return True
    except Exception:
        logger.exception("research.cache.publish_failed security=%s", security_id)
        return False


def run_research_pipeline(
    db: Session,
    *,
    ticker: str,
    exchange: str = "XNAS",
    market_date: date | None = None,
    trigger_type: str = "RESEARCH_FULL_REBUILD",
    settings: Settings | None = None,
) -> dict[str, Any]:
    """
    Outbox-style publication (Postgres-first):
    evidence → generate → validate →
    persist (artifact_pending + report_payload) → artifacts →
    mark published + latest pointer → derived cache.
    """
    settings = settings or get_settings()
    if not settings.research_engine_enabled:
        return {"ok": False, "error": "research_engine_disabled"}

    cache = get_research_cache(settings)
    lock_token: str | None = None
    security = None

    try:
        try:
            bundle = collect_internal_evidence(
                db, ticker=ticker, exchange=exchange, market_date=market_date
            )
        except EvidenceNotReady as exc:
            return {
                "ok": False,
                "retryable": True,
                "error": exc.code,
                "message": exc.message,
                "ticker": ticker.upper(),
            }

        if bundle.instrument_id is None or bundle.listing_id is None:
            return {"ok": False, "error": "instrument_mapping_missing", "ticker": ticker.upper()}

        security = get_or_create_security(
            db,
            ticker=bundle.ticker,
            exchange=bundle.exchange,
            instrument_id=bundle.instrument_id,
            listing_id=bundle.listing_id,
            display_name=bundle.instrument_name,
            tier=TIER_ACTIVE,
        )

        lock_token = acquire_generation_lock(
            cache, str(security.id), ttl_seconds=settings.research_generation_lock_ttl_seconds
        )
        if lock_token is None:
            existing = latest_version(db, security.id)
            return {
                "ok": True,
                "security_id": str(security.id),
                "version_id": str(existing.id) if existing else None,
                "decision": "lock_busy",
                "reused": True,
            }

        prior = latest_version(db, security.id)
        assessment = evaluate_material_change(
            bundle, prior_evidence_hash=prior.evidence_hash if prior else None
        )
        persist_assessment(db, security, bundle, assessment, prior.id if prior else None)

        dup = find_published_by_evidence(db, security.id, bundle.evidence_hash())
        if dup is not None or (prior and assessment.factors.get("identical_evidence")):
            reused = dup or prior
            assert reused is not None
            db.commit()
            report = load_recoverable_report(db, settings, reused) or {
                "executive_summary": reused.executive_summary
            }
            cache_ok = _try_publish_cache(db, settings, str(security.id), reused, report)
            if not cache_ok:
                from kyverance.research.jobs.queue import enqueue_job

                enqueue_job(
                    db,
                    job_type=JOB_CACHE_REPAIR,
                    idempotency_key=f"cache_repair:{security.id}:{reused.id}",
                    security_id=security.id,
                    payload={"security_id": str(security.id), "version_id": str(reused.id)},
                )
            return {
                "ok": True,
                "security_id": str(security.id),
                "version_id": str(reused.id),
                "decision": "reuse_identical",
                "reused": True,
                "assessment": {
                    "score": str(assessment.score),
                    "band": assessment.band,
                    "decision": assessment.decision,
                },
            }

        report = generate_canonical_report(bundle, assessment)
        try:
            assert_valid(report)
        except ResearchValidationError as exc:
            db.rollback()
            return {"ok": False, "error": "validation_failed", "message": str(exc)}

        version = persist_immutable_version(
            db,
            security=security,
            bundle=bundle,
            report=report,
            assessment=assessment,
            trigger_type=trigger_type,
            prior=prior,
            settings=settings,
        )
        db.commit()

        try:
            write_version_artifacts(settings, version, report)
            mark_artifact_ready(db, version)
            mark_published(db, version, prior)
            db.commit()
        except Exception as exc:  # noqa: BLE001
            logger.exception("research.publish.artifact_failed")
            db.rollback()
            version = db.get(type(version), version.id)
            if version:
                mark_artifact_failed(db, version)
                db.commit()
            return {
                "ok": False,
                "error": "artifact_failed",
                "message": str(exc),
                "version_id": str(version.id) if version else None,
                "publication_status": version.publication_status if version else None,
            }

        db.refresh(version)
        if version.publication_status != PUB_STATUS_PUBLISHED:
            return {
                "ok": False,
                "error": "publish_incomplete",
                "version_id": str(version.id),
                "publication_status": version.publication_status,
            }

        cache_ok = _try_publish_cache(db, settings, str(security.id), version, report)
        if not cache_ok:
            from kyverance.research.jobs.queue import enqueue_job

            enqueue_job(
                db,
                job_type=JOB_CACHE_REPAIR,
                idempotency_key=f"cache_repair:{security.id}:{version.id}",
                security_id=security.id,
                payload={"security_id": str(security.id), "version_id": str(version.id)},
            )

        return {
            "ok": True,
            "security_id": str(security.id),
            "version_id": str(version.id),
            "decision": assessment.decision,
            "reused": False,
            "publication_status": version.publication_status,
            "freshness_status": version.freshness_status or FRESHNESS_CURRENT,
            "evidence_hash": version.evidence_hash,
            "ai_enabled": False,
        }
    finally:
        if lock_token and security is not None:
            release_generation_lock(cache, str(security.id), lock_token)


def repair_cache_for_security(
    db: Session,
    security_id: str | UUID,
    settings: Settings | None = None,
    *,
    version_id: str | None = None,
) -> bool:
    from kyverance.research.models import SecurityResearchVersion

    settings = settings or get_settings()
    sid = UUID(str(security_id))
    if version_id:
        version = db.get(SecurityResearchVersion, UUID(str(version_id)))
    else:
        version = latest_version(db, sid)
    if not version or version.publication_status != PUB_STATUS_PUBLISHED:
        return False
    report = load_recoverable_report(db, settings, version)
    if not report:
        return False
    return _try_publish_cache(db, settings, str(sid), version, report)
