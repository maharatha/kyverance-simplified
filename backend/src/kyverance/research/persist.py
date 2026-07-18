"""Postgres-first research persistence and atomic publication (ADR 0005 Option A)."""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from kyverance.config import Settings, get_settings
from kyverance.research.artifacts import get_artifact_store, research_artifact_key
from kyverance.research.calendar import next_expected_refresh
from kyverance.research.constants import (
    FRESHNESS_CURRENT,
    FRESHNESS_SUPERSEDED,
    METHODOLOGY_VERSION,
    MODEL_VERSION,
    PROMPT_VERSION,
    PUB_STATUS_ARTIFACT_FAILED,
    PUB_STATUS_ARTIFACT_PENDING,
    PUB_STATUS_ARTIFACT_READY,
    PUB_STATUS_PUBLISHED,
    PUB_STATUS_VALIDATED,
    TIER_COLD,
)
from kyverance.research.evidence import EvidenceBundle
from kyverance.research.material_change import MaterialChangeResult
from kyverance.research.models import (
    MaterialChangeAssessment,
    ResearchSection,
    ResearchSecurity,
    SecurityResearchLatest,
    SecurityResearchVersion,
)

logger = logging.getLogger(__name__)


def get_or_create_security(
    db: Session,
    *,
    ticker: str,
    exchange: str,
    instrument_id: UUID,
    listing_id: UUID,
    display_name: str | None = None,
    tier: str = TIER_COLD,
) -> ResearchSecurity:
    row = (
        db.query(ResearchSecurity)
        .filter(
            ResearchSecurity.instrument_id == instrument_id,
            ResearchSecurity.listing_id == listing_id,
        )
        .one_or_none()
    )
    if row:
        if display_name and not row.display_name:
            row.display_name = display_name
        db.flush()
        return row
    by_ticker = (
        db.query(ResearchSecurity)
        .filter(ResearchSecurity.ticker == ticker.upper(), ResearchSecurity.exchange == exchange.upper())
        .one_or_none()
    )
    if by_ticker:
        return by_ticker
    row = ResearchSecurity(
        id=uuid4(),
        instrument_id=instrument_id,
        listing_id=listing_id,
        ticker=ticker.upper(),
        exchange=exchange.upper(),
        display_name=display_name or ticker.upper(),
        research_tier=tier,
        status="active",
    )
    db.add(row)
    db.flush()
    return row


def latest_version(db: Session, security_id: UUID) -> SecurityResearchVersion | None:
    ptr = db.get(SecurityResearchLatest, security_id)
    if not ptr:
        return None
    version = db.get(SecurityResearchVersion, ptr.version_id)
    if version and version.publication_status != PUB_STATUS_PUBLISHED:
        return None
    return version


def load_recoverable_report(
    db: Session,
    settings: Settings,
    version: SecurityResearchVersion,
) -> dict[str, Any] | None:
    if version.artifact_key:
        store = get_artifact_store(settings)
        from_store = store.get_json(version.artifact_key)
        if from_store:
            return from_store
    if isinstance(version.report_payload, dict) and version.report_payload:
        return dict(version.report_payload)
    rows = db.query(ResearchSection).filter(ResearchSection.version_id == version.id).all()
    if not rows and not version.executive_summary:
        return None
    return {
        "ticker": version.ticker,
        "exchange": version.exchange,
        "market_date": version.market_date,
        "executive_summary": version.executive_summary,
        "confidence_score": float(version.confidence_score or 0),
        "change_summary": version.change_summary,
        "changed_sections": version.changed_sections or [],
        "sections": {r.section_key: r.content for r in rows},
        "evidence_hash": version.evidence_hash,
        "model_version": version.model_version,
        "prompt_version": version.prompt_version,
        "methodology_version": version.methodology_version,
        "ai_enabled": False,
    }


def persist_assessment(
    db: Session,
    security: ResearchSecurity,
    bundle: EvidenceBundle,
    assessment: MaterialChangeResult,
    prior_version_id: UUID | None,
) -> MaterialChangeAssessment:
    row = MaterialChangeAssessment(
        id=uuid4(),
        security_id=security.id,
        market_date=bundle.market_date.isoformat(),
        score=assessment.score,
        band=assessment.band,
        decision=assessment.decision,
        factors=assessment.factors,
        prior_version_id=prior_version_id,
    )
    db.add(row)
    db.flush()
    return row


def find_published_by_evidence(
    db: Session, security_id: UUID, evidence_hash: str
) -> SecurityResearchVersion | None:
    return (
        db.query(SecurityResearchVersion)
        .filter(
            SecurityResearchVersion.security_id == security_id,
            SecurityResearchVersion.evidence_hash == evidence_hash,
            SecurityResearchVersion.methodology_version == METHODOLOGY_VERSION,
            SecurityResearchVersion.model_version == MODEL_VERSION,
            SecurityResearchVersion.prompt_version == PROMPT_VERSION,
            SecurityResearchVersion.publication_status == PUB_STATUS_PUBLISHED,
        )
        .order_by(SecurityResearchVersion.generated_at.desc())
        .first()
    )


def persist_immutable_version(
    db: Session,
    *,
    security: ResearchSecurity,
    bundle: EvidenceBundle,
    report: dict[str, Any],
    assessment: MaterialChangeResult,
    trigger_type: str,
    prior: SecurityResearchVersion | None,
    settings: Settings | None = None,
) -> SecurityResearchVersion:
    settings = settings or get_settings()
    now = datetime.now(timezone.utc)
    version_id = uuid4()
    artifact_key = research_artifact_key(
        security.ticker, bundle.market_date.isoformat(), str(version_id), "report.json"
    )
    refresh_at = next_expected_refresh(
        db,
        bundle.market_date,
        lag_minutes=settings.research_eod_finalize_lag_minutes,
        exchange_code=security.exchange,
    )
    version = SecurityResearchVersion(
        id=version_id,
        security_id=security.id,
        ticker=security.ticker,
        exchange=security.exchange,
        market_date=bundle.market_date.isoformat(),
        generated_at=now,
        published_at=None,
        prior_version_id=prior.id if prior else None,
        trigger_type=trigger_type,
        material_change_score=assessment.score,
        changed_sections=report.get("changed_sections") or [],
        model_version=MODEL_VERSION,
        prompt_version=PROMPT_VERSION,
        methodology_version=METHODOLOGY_VERSION,
        evidence_hash=bundle.evidence_hash(),
        confidence_score=Decimal(str(report.get("confidence_score") or 0.7)),
        validation_status=PUB_STATUS_VALIDATED,
        publication_status=PUB_STATUS_ARTIFACT_PENDING,
        freshness_status=FRESHNESS_CURRENT,
        artifact_key=artifact_key,
        change_summary=report.get("change_summary"),
        executive_summary=report.get("executive_summary"),
        report_payload=report,
        evidence_refs=report.get("evidence_refs") or [],
        next_expected_refresh=refresh_at,
        source_data_timestamp=bundle.source_data_timestamp,
        valid_through=refresh_at,
    )
    db.add(version)
    db.flush()
    for key, content in (report.get("sections") or {}).items():
        db.add(
            ResearchSection(
                id=uuid4(),
                version_id=version.id,
                security_id=security.id,
                section_key=key,
                evidence_hash=bundle.evidence_hash(),
                content=content if isinstance(content, dict) else {"summary": content},
            )
        )
    db.flush()
    return version


def write_version_artifacts(settings: Settings, version: SecurityResearchVersion, report: dict[str, Any]) -> str:
    store = get_artifact_store(settings)
    key = version.artifact_key or research_artifact_key(
        version.ticker, version.market_date, str(version.id)
    )
    store.put_json(key, report)
    return key


def mark_artifact_ready(db: Session, version: SecurityResearchVersion) -> None:
    version.publication_status = PUB_STATUS_ARTIFACT_READY
    db.flush()


def mark_artifact_failed(db: Session, version: SecurityResearchVersion) -> None:
    version.publication_status = PUB_STATUS_ARTIFACT_FAILED
    db.flush()


def mark_published(
    db: Session, version: SecurityResearchVersion, prior: SecurityResearchVersion | None
) -> None:
    """Atomic Postgres publish + latest pointer. Cache is derived afterward."""
    now = datetime.now(timezone.utc)
    version.published_at = now
    version.publication_status = PUB_STATUS_PUBLISHED
    version.freshness_status = FRESHNESS_CURRENT
    if prior and prior.id != version.id and prior.publication_status == PUB_STATUS_PUBLISHED:
        prior.freshness_status = FRESHNESS_SUPERSEDED
    ptr = db.get(SecurityResearchLatest, version.security_id)
    if ptr is None:
        db.add(SecurityResearchLatest(security_id=version.security_id, version_id=version.id))
    else:
        ptr.version_id = version.id
        ptr.updated_at = now
    db.flush()


def finalize_publication(
    db: Session,
    settings: Settings,
    version: SecurityResearchVersion,
) -> bool:
    """Ensure artifacts exist then mark published if not already."""
    if version.publication_status == PUB_STATUS_PUBLISHED:
        return True
    report = load_recoverable_report(db, settings, version)
    if not report:
        mark_artifact_failed(db, version)
        db.commit()
        return False
    try:
        write_version_artifacts(settings, version, report)
        mark_artifact_ready(db, version)
        prior = None
        if version.prior_version_id:
            prior = db.get(SecurityResearchVersion, version.prior_version_id)
        mark_published(db, version, prior)
        db.commit()
        return True
    except Exception:
        logger.exception("research.finalize_publication.failed version=%s", version.id)
        mark_artifact_failed(db, version)
        db.commit()
        return False
