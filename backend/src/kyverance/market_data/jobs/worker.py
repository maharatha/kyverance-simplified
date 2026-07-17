"""Market-data worker — drains market_data_jobs. Never serves customer requests."""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any

from kyverance.config import get_settings, refresh_settings
from kyverance.db.session import SessionLocal
from kyverance.market_data.jobs import queue
from kyverance.market_data.jobs.correction import run_correction
from kyverance.market_data.jobs.daily_eod import run_daily_eod
from kyverance.market_data.jobs.reconcile import run_reconcile
from kyverance.market_data.jobs.sync_exchanges import sync_exchanges
from kyverance.market_data.jobs.sync_instruments import sync_instruments
from kyverance.market_data.jobs.types import (
    JOB_CORRECTION,
    JOB_DAILY_EOD,
    JOB_RECONCILE,
    JOB_SYNC_EXCHANGES,
    JOB_SYNC_INSTRUMENTS,
)
from kyverance.market_data.models import MarketDataHealth, MarketDataJob

logger = logging.getLogger(__name__)


async def execute_job(job_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    db = SessionLocal()
    try:
        if job_type == JOB_SYNC_EXCHANGES:
            return await sync_exchanges(db)
        if job_type == JOB_SYNC_INSTRUMENTS:
            return await sync_instruments(
                db,
                exchange_canonical=payload.get("exchange", "XNAS"),
                limit=payload.get("limit"),
            )
        if job_type == JOB_DAILY_EOD:
            return await run_daily_eod(
                db,
                exchange_canonical=payload.get("exchange", "XNAS"),
                trading_date=payload["trading_date"],
            )
        if job_type == JOB_CORRECTION:
            return await run_correction(
                db,
                exchange_canonical=payload.get("exchange", "XNAS"),
                trading_date=payload["trading_date"],
            )
        if job_type == JOB_RECONCILE:
            return run_reconcile(
                db,
                exchange_canonical=payload.get("exchange", "XNAS"),
                trading_date=payload["trading_date"],
            )
        raise ValueError(f"Unknown market_data job_type={job_type}")
    finally:
        db.close()


def run_once(max_jobs: int | None = None) -> dict[str, Any]:
    settings = get_settings()
    if not settings.market_data_jobs_enabled:
        return {"processed": 0, "skipped": "market_data_jobs_disabled", "jobs": []}

    limit = max_jobs if max_jobs is not None else settings.market_data_worker_max_jobs
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
            payload = dict(job.payload or {})
            attempt = int(job.attempts or 0)
            correlation_id = job.correlation_id
        finally:
            db.close()

        try:
            result = asyncio.run(execute_job(job_type, payload))
            if queue.job_should_retry(result):
                raise RuntimeError(
                    f"market_data soft-fail status={result.get('status')} "
                    f"error={result.get('error_message') or result.get('error_code') or 'validation_failed'}"
                )
            db = SessionLocal()
            try:
                row = db.get(MarketDataJob, job_id)
                if row:
                    queue.complete_job(db, row, result)
                health = db.get(MarketDataHealth, "worker")
                if health is None:
                    health = MarketDataHealth(component="worker")
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
                    "status": (result or {}).get("status"),
                }
            )
            logger.info(
                "market_data.worker.done job_id=%s type=%s correlation=%s",
                job_id,
                job_type,
                correlation_id,
            )
        except Exception as exc:  # noqa: BLE001
            db = SessionLocal()
            try:
                row = db.get(MarketDataJob, job_id)
                outcome = "failed"
                if row:
                    outcome = queue.fail_job(db, row, str(exc))
                health = db.get(MarketDataHealth, "worker")
                if health is None:
                    health = MarketDataHealth(component="worker")
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
            logger.exception("market_data.worker.failed job_id=%s", job_id)
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
    mode = (os.environ.get("MARKET_DATA_WORKER_MODE") or settings.market_data_worker_mode or "once").lower()
    if "--once" in args or mode in {"once", "drain"}:
        report = run_once()
        logger.info(
            "market_data.worker.exit processed=%s jobs=%s",
            report.get("processed"),
            len(report.get("jobs") or []),
        )
        return
    raise SystemExit("Only --once / MARKET_DATA_WORKER_MODE=once is supported in MRKT-01")


if __name__ == "__main__":
    main()
