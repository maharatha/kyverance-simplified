"""Postgres-backed market_data_jobs queue with SQLite-safe claim fallback."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from kyverance.config import get_settings
from kyverance.market_data.constants import (
    BACKOFF_BASE_SECONDS,
    JOB_STATUS_DEAD,
    JOB_STATUS_DONE,
    JOB_STATUS_PENDING,
    JOB_STATUS_RUNNING,
)
from kyverance.market_data.models import MarketDataJob


def _lock_seconds() -> int:
    return max(60, int(get_settings().market_data_job_lock_seconds or 1800))


def enqueue_job(
    db: Session,
    *,
    job_type: str,
    idempotency_key: str,
    payload: dict[str, Any] | None = None,
    correlation_id: str | None = None,
) -> MarketDataJob:
    existing = (
        db.query(MarketDataJob).filter(MarketDataJob.idempotency_key == idempotency_key).one_or_none()
    )
    if existing:
        return existing

    job = MarketDataJob(
        id=uuid4(),
        job_type=job_type,
        status=JOB_STATUS_PENDING,
        payload=payload or {},
        idempotency_key=idempotency_key,
        correlation_id=correlation_id or str(uuid4()),
    )
    db.add(job)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = (
            db.query(MarketDataJob)
            .filter(MarketDataJob.idempotency_key == idempotency_key)
            .one_or_none()
        )
        if existing is None:
            raise
        return existing
    db.refresh(job)
    return job


def claim_next_job(db: Session) -> MarketDataJob | None:
    now = datetime.now(timezone.utc)
    bind = db.get_bind()
    dialect = bind.dialect.name if bind is not None else ""

    if dialect == "postgresql":
        row = db.execute(
            text(
                """
                SELECT id FROM market_data_jobs
                WHERE status = 'pending'
                  AND (locked_until IS NULL OR locked_until < :now)
                  AND attempts < max_attempts
                ORDER BY created_at ASC
                FOR UPDATE SKIP LOCKED
                LIMIT 1
                """
            ),
            {"now": now},
        ).first()
        if not row:
            return None
        job = db.get(MarketDataJob, row[0])
    else:
        job = (
            db.query(MarketDataJob)
            .filter(
                MarketDataJob.status == JOB_STATUS_PENDING,
                MarketDataJob.attempts < MarketDataJob.max_attempts,
            )
            .filter(
                (MarketDataJob.locked_until.is_(None)) | (MarketDataJob.locked_until < now)  # type: ignore[operator]
            )
            .order_by(MarketDataJob.created_at.asc())
            .first()
        )

    if not job:
        return None
    job.status = JOB_STATUS_RUNNING
    job.attempts = int(job.attempts or 0) + 1
    job.locked_until = now + timedelta(seconds=_lock_seconds())
    job.updated_at = now
    db.commit()
    db.refresh(job)
    return job


def complete_job(db: Session, job: MarketDataJob, result: dict[str, Any] | None = None) -> None:
    job.status = JOB_STATUS_DONE
    job.result = result
    job.locked_until = None
    job.updated_at = datetime.now(timezone.utc)
    db.commit()


def fail_job(db: Session, job: MarketDataJob, error: str) -> str:
    """Mark job failed. Returns 'dead' or 'retry_scheduled'."""
    now = datetime.now(timezone.utc)
    job.last_error = error[:2000]
    job.updated_at = now
    if int(job.attempts or 0) >= int(job.max_attempts or 5):
        job.status = JOB_STATUS_DEAD
        job.locked_until = None
        db.commit()
        return "dead"
    job.status = JOB_STATUS_PENDING
    backoff = BACKOFF_BASE_SECONDS * (2 ** max(0, int(job.attempts or 1) - 1))
    job.locked_until = now + timedelta(seconds=backoff)
    db.commit()
    return "retry_scheduled"


def job_should_retry(result: dict[str, Any] | None) -> bool:
    status = str((result or {}).get("status") or "").upper()
    return status in {"FAILED", "PARTIALLY_FAILED"}
