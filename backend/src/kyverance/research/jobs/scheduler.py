"""Exchange-aware research scheduler — enqueues only; never generates inline."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import uuid4

from kyverance.config import get_settings, refresh_settings
from kyverance.db.session import SessionLocal
from kyverance.research.calendar import is_trading_day, latest_completed_session, next_trading_day, us_market_date
from kyverance.research.constants import (
    JOB_FRESHNESS_CHECK,
    JOB_FULL_REBUILD,
    PUB_STATUS_PUBLISHED,
    TIER_ACTIVE,
    TIER_COLD,
    TIER_HOT,
)
from kyverance.research.jobs.queue import enqueue_job
from kyverance.research.models import ResearchHealth, ResearchSchedulerRun, ResearchSecurity, SecurityResearchVersion
from kyverance.simulation.models import SimPosition

logger = logging.getLogger(__name__)


def apply_tier_rules(db) -> dict:
    now = datetime.now(timezone.utc)
    held_symbols = {row.symbol.upper() for row in db.query(SimPosition.symbol).distinct().all()}
    changed = 0
    for sec in db.query(ResearchSecurity).filter(ResearchSecurity.status == "active").all():
        prior = sec.research_tier
        reason = sec.tier_reason
        if sec.ticker.upper() in held_symbols:
            sec.research_tier = TIER_HOT
            sec.tier_reason = "held_in_simulation"
        else:
            has_pub = (
                db.query(SecurityResearchVersion.id)
                .filter(
                    SecurityResearchVersion.security_id == sec.id,
                    SecurityResearchVersion.publication_status == PUB_STATUS_PUBLISHED,
                )
                .first()
            )
            if has_pub:
                sec.research_tier = TIER_ACTIVE
                sec.tier_reason = "has_published_research"
            else:
                sec.research_tier = TIER_COLD
                sec.tier_reason = "on_demand_only"
        if prior != sec.research_tier or reason != sec.tier_reason:
            sec.tier_changed_at = now
            changed += 1
    db.commit()
    return {"tier_updates": changed}


def schedule_once(*, as_of: datetime | None = None) -> dict:
    settings = get_settings()
    if not settings.research_jobs_enabled or not settings.research_engine_enabled:
        return {"ok": False, "skipped": "research_disabled"}

    now = as_of or datetime.now(timezone.utc)
    db = SessionLocal()
    session_day = latest_completed_session(
        db, now, lag_minutes=settings.research_eod_finalize_lag_minutes
    )
    run = ResearchSchedulerRun(
        id=uuid4(),
        started_at=now,
        status="running",
        session_day=session_day.isoformat(),
    )
    db.add(run)
    db.commit()

    try:
        if not is_trading_day(db, session_day):
            result = {
                "ok": True,
                "skipped": "non_trading_day",
                "session_day": session_day.isoformat(),
            }
            run.status = "skipped"
            run.finished_at = datetime.now(timezone.utc)
            run.result = result
            db.commit()
            return result

        apply_tier_rules(db)
        enqueued = 0
        securities = db.query(ResearchSecurity).filter(ResearchSecurity.status == "active").all()
        for sec in securities:
            tier = (sec.research_tier or TIER_COLD).lower()
            if tier == TIER_COLD:
                continue
            enqueue_job(
                db,
                job_type=JOB_FULL_REBUILD,
                idempotency_key=f"eod_rebuild:{sec.id}:{session_day.isoformat()}",
                security_id=sec.id,
                payload={
                    "ticker": sec.ticker,
                    "exchange": sec.exchange,
                    "market_date": session_day.isoformat(),
                },
            )
            enqueued += 1

        enqueue_job(
            db,
            job_type=JOB_FRESHNESS_CHECK,
            idempotency_key=f"freshness_pass:{session_day.isoformat()}",
            payload={"session_day": session_day.isoformat()},
        )

        result = {
            "ok": True,
            "session_day": session_day.isoformat(),
            "today_et": us_market_date(now).isoformat(),
            "enqueued": enqueued,
            "securities": len(securities),
            "next_session": next_trading_day(db, session_day).isoformat(),
            "run_id": str(run.id),
            "inline_generation": False,
        }
        run.status = "ok"
        run.finished_at = datetime.now(timezone.utc)
        run.result = result
        health = db.get(ResearchHealth, "scheduler")
        if health is None:
            health = ResearchHealth(component="scheduler")
            db.add(health)
        health.last_success_at = datetime.now(timezone.utc)
        health.last_message = f"enqueued={enqueued} session={session_day.isoformat()}"
        health.updated_at = datetime.now(timezone.utc)
        db.commit()
        logger.info("research.scheduler.ok %s", result)
        return result
    except Exception as exc:  # noqa: BLE001
        run.status = "error"
        run.finished_at = datetime.now(timezone.utc)
        run.result = {"ok": False, "error": str(exc)}
        db.commit()
        raise
    finally:
        db.close()


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    refresh_settings()
    result = schedule_once()
    logger.info("research.scheduler.result %s", result)


if __name__ == "__main__":
    main()
