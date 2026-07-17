"""Local/dev warehouse bootstrap — seeds fake listings + EOD offline."""

from __future__ import annotations

import asyncio
import logging

from sqlalchemy.orm import Session

from kyverance.config import Settings, get_settings
from kyverance.db.session import SessionLocal
from kyverance.market_data.models import InstrumentListing

logger = logging.getLogger(__name__)


def warehouse_needs_seed(db: Session) -> bool:
    return db.query(InstrumentListing).count() == 0


async def seed_fake_warehouse(db: Session) -> dict:
    from kyverance.market_data.jobs.daily_eod import run_daily_eod
    from kyverance.market_data.jobs.sync_exchanges import sync_exchanges
    from kyverance.market_data.jobs.sync_instruments import sync_instruments

    out: dict = {"sync_exchanges": await sync_exchanges(db)}
    out["sync_instruments"] = await sync_instruments(db, exchange_canonical="XNAS", limit=20)
    published = []
    for day in (
        "2026-07-01",
        "2026-07-02",
        "2026-07-06",
        "2026-07-07",
        "2026-07-08",
        "2026-07-09",
        "2026-07-10",
    ):
        try:
            published.append(await run_daily_eod(db, exchange_canonical="XNAS", trading_date=day))
        except Exception as exc:  # noqa: BLE001
            logger.warning("market_data.bootstrap.eod_day_failed day=%s err=%s", day, exc)
    out["daily_eod"] = published
    return out


def ensure_fake_warehouse_seed(settings: Settings | None = None) -> dict | None:
    s = settings or get_settings()
    if (s.market_data_provider or "").strip().lower() not in {"fake", "mock"}:
        return None
    if not s.market_data_engine_enabled:
        return None
    db = SessionLocal()
    try:
        if not warehouse_needs_seed(db):
            return {"skipped": True, "reason": "listings_present"}
        logger.info("market_data.bootstrap.seeding_fake_warehouse")
        result = asyncio.run(seed_fake_warehouse(db))
        logger.info("market_data.bootstrap.done")
        return result
    except Exception as exc:  # noqa: BLE001
        logger.exception("market_data.bootstrap.failed: %s", exc)
        return {"error": str(exc)}
    finally:
        db.close()
