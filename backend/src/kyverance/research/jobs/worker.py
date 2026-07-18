"""Research worker — drains research_jobs. Never serves customer deep generation."""

from __future__ import annotations

import logging
import os
import sys
from datetime import date, datetime, timezone
from typing import Any
from uuid import UUID

from kyverance.config import get_settings, refresh_settings
from kyverance.db.session import SessionLocal

# Register ORM mappers used by claim/execute paths (portfolio/wallet relationships).
import kyverance.market_data.models  # noqa: F401
import kyverance.portfolios.models  # noqa: F401
import kyverance.research.models  # noqa: F401
import kyverance.simulation.models  # noqa: F401
from kyverance.research.constants import (
    FRESHNESS_STALE,
    JOB_CACHE_REPAIR,
    JOB_COLD_ON_DEMAND,
    JOB_FRESHNESS_CHECK,
    JOB_FULL_REBUILD,
    JOB_PUBLISH,
    JOB_VALIDATE,
    PUB_STATUS_PUBLISHED,
)
from kyverance.research.jobs import queue
from kyverance.research.models import ResearchHealth, ResearchJob, SecurityResearchVersion
from kyverance.research.pipeline import repair_cache_for_security, run_research_pipeline

logger = logging.getLogger(__name__)


def execute_job(db, job: ResearchJob) -> dict[str, Any]:
    payload = job.payload or {}
    ticker = str(payload.get("ticker") or "").upper()
    exchange = str(payload.get("exchange") or "XNAS").upper()
    market_date_raw = payload.get("market_date")
    market_date = date.fromisoformat(market_date_raw) if market_date_raw else None
    settings = get_settings()

    if job.job_type in {JOB_FULL_REBUILD, JOB_COLD_ON_DEMAND}:
        if not ticker:
            return {"ok": False, "error": "missing_ticker"}
        return run_research_pipeline(
            db,
            ticker=ticker,
            exchange=exchange,
            market_date=market_date,
            trigger_type=job.job_type,
            settings=settings,
        )

    if job.job_type in {JOB_CACHE_REPAIR, JOB_PUBLISH}:
        sid = payload.get("security_id") or (str(job.security_id) if job.security_id else None)
        vid = payload.get("version_id")
        if job.job_type == JOB_PUBLISH and vid:
            from kyverance.research.persist import finalize_publication

            version = db.get(SecurityResearchVersion, UUID(str(vid)))
            if not version:
                return {"ok": False, "error": "version_not_found"}
            ok = finalize_publication(db, settings, version)
            return {"ok": ok, "version_id": str(version.id), "publication_status": version.publication_status}
        if not sid:
            return {"ok": False, "error": "missing_security_id"}
        ok = repair_cache_for_security(db, sid, settings, version_id=vid)
        return {"ok": ok, "security_id": sid, "version_id": vid}

    if job.job_type == JOB_VALIDATE:
        from kyverance.research.persist import load_recoverable_report
        from kyverance.research.validate import validate_research_report

        vid = payload.get("version_id")
        if not vid:
            return {"ok": False, "error": "missing_version_id"}
        version = db.get(SecurityResearchVersion, UUID(str(vid)))
        if not version:
            return {"ok": False, "error": "version_not_found"}
        report = load_recoverable_report(db, settings, version) or {}
        errors = validate_research_report(report)
        return {"ok": not errors, "errors": errors}

    if job.job_type == JOB_FRESHNESS_CHECK:
        return run_freshness_pass(db, settings)

    return {"ok": True, "skipped": job.job_type}


def run_freshness_pass(db, settings) -> dict[str, Any]:
    from kyverance.research.calendar import latest_completed_session
    from kyverance.research.jobs.queue import enqueue_job

    now = datetime.now(timezone.utc)
    stale_rows = (
        db.query(SecurityResearchVersion)
        .filter(
            SecurityResearchVersion.publication_status == PUB_STATUS_PUBLISHED,
            SecurityResearchVersion.freshness_status.in_(("CURRENT", "STALE")),
            SecurityResearchVersion.next_expected_refresh.isnot(None),
            SecurityResearchVersion.next_expected_refresh < now,
        )
        .limit(200)
        .all()
    )
    enqueued = 0
    session_day = latest_completed_session(
        db, now, lag_minutes=settings.research_eod_finalize_lag_minutes
    )
    for row in stale_rows:
        if row.freshness_status != FRESHNESS_STALE:
            row.freshness_status = FRESHNESS_STALE
        day = session_day.isoformat()
        enqueue_job(
            db,
            job_type=JOB_FULL_REBUILD,
            idempotency_key=f"freshness:{row.security_id}:{day}",
            security_id=row.security_id,
            payload={"ticker": row.ticker, "exchange": row.exchange, "market_date": day},
        )
        enqueued += 1
    db.commit()
    return {
        "ok": True,
        "stale_marked": len(stale_rows),
        "enqueued": enqueued,
        "session_day": session_day.isoformat(),
    }


def run_once(max_jobs: int | None = None) -> dict[str, Any]:
    settings = get_settings()
    if not settings.research_jobs_enabled:
        return {"processed": 0, "skipped": "research_jobs_disabled", "jobs": []}

    limit = max_jobs if max_jobs is not None else settings.research_worker_max_jobs
    started = datetime.now(timezone.utc)
    processed = 0
    job_results: list[dict[str, Any]] = []

    while processed < limit:
        db = SessionLocal()
        try:
            job = queue.claim_next_job(db)
            if not job:
                break
            job_id = job.id
            job_type = job.job_type
            correlation_id = job.correlation_id
            attempt = int(job.attempts or 0)
        finally:
            db.close()

        try:
            db = SessionLocal()
            try:
                row = db.get(ResearchJob, job_id)
                if not row:
                    continue
                result = execute_job(db, row)
                if isinstance(result, dict) and result.get("ok") is False:
                    raise RuntimeError(str(result.get("error") or result.get("message") or result))
                queue.complete_job(db, row, result if isinstance(result, dict) else {"result": result})
                health = db.get(ResearchHealth, "worker")
                if health is None:
                    health = ResearchHealth(component="worker")
                    db.add(health)
                health.last_success_at = datetime.now(timezone.utc)
                health.last_message = f"done type={job_type} correlation={correlation_id}"
                health.updated_at = datetime.now(timezone.utc)
                db.commit()
            finally:
                db.close()
            job_results.append(
                {
                    "jobType": job_type,
                    "correlationId": correlation_id,
                    "attempt": attempt,
                    "outcome": "done",
                }
            )
        except Exception as exc:  # noqa: BLE001
            db = SessionLocal()
            try:
                row = db.get(ResearchJob, job_id)
                outcome = "failed"
                if row:
                    outcome = queue.fail_job(db, row, str(exc))
                health = db.get(ResearchHealth, "worker")
                if health is None:
                    health = ResearchHealth(component="worker")
                    db.add(health)
                health.last_error_at = datetime.now(timezone.utc)
                health.last_message = str(exc)[:2000]
                health.updated_at = datetime.now(timezone.utc)
                db.commit()
            finally:
                db.close()
            job_results.append(
                {
                    "jobType": job_type,
                    "correlationId": correlation_id,
                    "attempt": attempt,
                    "outcome": outcome,
                    "error": str(exc)[:500],
                }
            )
            logger.exception("research.worker.failed job_id=%s", job_id)
        processed += 1

    return {
        "processed": processed,
        "maxJobs": limit,
        "startedAt": started.isoformat(),
        "finishedAt": datetime.now(timezone.utc).isoformat(),
        "jobs": job_results,
    }


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO)
    refresh_settings()
    args = argv if argv is not None else sys.argv[1:]
    settings = get_settings()
    mode = (os.environ.get("RESEARCH_WORKER_MODE") or settings.research_worker_mode or "once").lower()
    if "--once" in args or mode in {"once", "drain"}:
        report = run_once()
        logger.info(
            "research.worker.exit processed=%s jobs=%s",
            report.get("processed"),
            len(report.get("jobs") or []),
        )
        return
    raise SystemExit("Only --once / RESEARCH_WORKER_MODE=once is supported in RSRCH-01")


if __name__ == "__main__":
    main()
