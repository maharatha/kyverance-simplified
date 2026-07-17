"""Correction pass — re-fetch and bump data_version when values change."""

from __future__ import annotations

from sqlalchemy.orm import Session

from kyverance.market_data.constants import JOB_CORRECTION
from kyverance.market_data.jobs.daily_eod import run_daily_eod


async def run_correction(db: Session, *, exchange_canonical: str, trading_date: str) -> dict:
    return await run_daily_eod(
        db,
        exchange_canonical=exchange_canonical,
        trading_date=trading_date,
        job_type=JOB_CORRECTION,
        bump_version=True,
    )
