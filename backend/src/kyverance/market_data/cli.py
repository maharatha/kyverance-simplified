"""CLI entrypoints for market-data scheduler, worker, and admin helpers."""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys

from kyverance.config import refresh_settings
from kyverance.db.session import SessionLocal
from kyverance.market_data.bootstrap import ensure_fake_warehouse_seed
from kyverance.market_data.jobs import scheduler as market_scheduler
from kyverance.market_data.jobs import worker as market_worker
from kyverance.market_data.jobs.correction import run_correction
from kyverance.market_data.jobs.daily_eod import run_daily_eod
from kyverance.market_data.jobs.reconcile import run_reconcile
from kyverance.market_data.jobs.sync_exchanges import sync_exchanges
from kyverance.market_data.jobs.sync_instruments import sync_instruments

logger = logging.getLogger(__name__)


def scheduler_main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO)
    refresh_settings()
    _ = argv
    result = market_scheduler.schedule_once()
    logger.info("market_data.scheduler.result %s", result)


def worker_main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO)
    refresh_settings()
    args = list(argv if argv is not None else sys.argv[1:])
    if "--once" not in args:
        args = ["--once", *args]
    market_worker.main(args)


def admin_main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO)
    refresh_settings()
    parser = argparse.ArgumentParser(prog="kyverance-market-admin")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("seed-fake")
    p_sync_ex = sub.add_parser("sync-exchanges")
    _ = p_sync_ex
    p_sync_inst = sub.add_parser("sync-instruments")
    p_sync_inst.add_argument("--exchange", default="XNAS")
    p_sync_inst.add_argument("--limit", type=int, default=0)
    p_eod = sub.add_parser("daily-eod")
    p_eod.add_argument("--exchange", default="XNAS")
    p_eod.add_argument("--date", required=True)
    p_corr = sub.add_parser("correction")
    p_corr.add_argument("--exchange", default="XNAS")
    p_corr.add_argument("--date", required=True)
    p_rec = sub.add_parser("reconcile")
    p_rec.add_argument("--exchange", default="XNAS")
    p_rec.add_argument("--date", required=True)

    args = parser.parse_args(argv)
    db = SessionLocal()
    try:
        if args.command == "seed-fake":
            result = ensure_fake_warehouse_seed()
            logger.info("seed-fake %s", result)
            return
        if args.command == "sync-exchanges":
            result = asyncio.run(sync_exchanges(db))
        elif args.command == "sync-instruments":
            limit = args.limit if args.limit > 0 else None
            result = asyncio.run(
                sync_instruments(db, exchange_canonical=args.exchange, limit=limit)
            )
        elif args.command == "daily-eod":
            result = asyncio.run(
                run_daily_eod(db, exchange_canonical=args.exchange, trading_date=args.date)
            )
        elif args.command == "correction":
            result = asyncio.run(
                run_correction(db, exchange_canonical=args.exchange, trading_date=args.date)
            )
        elif args.command == "reconcile":
            result = run_reconcile(db, exchange_canonical=args.exchange, trading_date=args.date)
        else:
            raise SystemExit(f"unknown command {args.command}")
        logger.info("%s %s", args.command, result)
    finally:
        db.close()


if __name__ == "__main__":
    admin_main(sys.argv[1:])
