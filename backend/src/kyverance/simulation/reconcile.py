"""Recompute cash from ledger and quantities from lots; block mutations on mismatch."""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from kyverance.audit.service import record_audit_event
from kyverance.simulation.constants import AUDIT_RECON_BLOCK
from kyverance.simulation.models import (
    ReconciliationIncident,
    SimPosition,
    SimPositionLot,
    SimWallet,
    WalletLedgerEntry,
)
from kyverance.simulation.money import money, money_str, qty, qty_str


def ledger_sum(db: Session, wallet_id: uuid.UUID) -> Decimal:
    total = (
        db.query(func.coalesce(func.sum(WalletLedgerEntry.amount), 0))
        .filter(WalletLedgerEntry.wallet_id == wallet_id)
        .scalar()
    )
    return money(total)


def lots_sum(db: Session, portfolio_id: uuid.UUID, symbol: str) -> Decimal:
    total = (
        db.query(func.coalesce(func.sum(SimPositionLot.quantity_remaining), 0))
        .filter(
            SimPositionLot.portfolio_id == portfolio_id,
            SimPositionLot.symbol == symbol,
        )
        .scalar()
    )
    return qty(total)


def reconcile_portfolio(db: Session, *, wallet: SimWallet, portfolio_id: uuid.UUID) -> dict[str, Any]:
    cash_ledger = ledger_sum(db, wallet.id)
    cash_cached = money(wallet.balance)
    complimentary = money(wallet.complimentary_balance)
    cash_ok = cash_ledger == cash_cached and complimentary == cash_cached

    positions = (
        db.query(SimPosition).filter(SimPosition.portfolio_id == portfolio_id).order_by(SimPosition.symbol).all()
    )
    position_rows: list[dict[str, Any]] = []
    positions_ok = True
    for pos in positions:
        lot_total = lots_sum(db, portfolio_id, pos.symbol)
        row_ok = lot_total == qty(pos.quantity)
        positions_ok = positions_ok and row_ok
        position_rows.append(
            {
                "symbol": pos.symbol,
                "position_quantity": qty_str(pos.quantity),
                "lots_sum": qty_str(lot_total),
                "ok": row_ok,
            }
        )

    # Orphan lots with no position row.
    lot_symbols = {
        row[0]
        for row in db.query(SimPositionLot.symbol)
        .filter(SimPositionLot.portfolio_id == portfolio_id, SimPositionLot.quantity_remaining > 0)
        .distinct()
        .all()
    }
    pos_symbols = {p.symbol for p in positions}
    orphan_lots = sorted(lot_symbols - pos_symbols)
    if orphan_lots:
        positions_ok = False

    ok = cash_ok and positions_ok and not orphan_lots
    return {
        "portfolio_id": str(portfolio_id),
        "wallet_id": str(wallet.id),
        "ok": ok,
        "cash": {
            "ledger_sum": money_str(cash_ledger),
            "cached_balance": money_str(cash_cached),
            "complimentary_balance": money_str(complimentary),
            "ok": cash_ok,
            "delta": money_str(cash_cached - cash_ledger),
        },
        "positions": position_rows,
        "orphan_lot_symbols": orphan_lots,
        "positions_ok": positions_ok,
    }


def require_reconciled(
    db: Session,
    *,
    wallet: SimWallet,
    portfolio_id: uuid.UUID,
    owner_user_id: uuid.UUID,
    actor_subject: str,
) -> dict[str, Any]:
    report = reconcile_portfolio(db, wallet=wallet, portfolio_id=portfolio_id)
    if report["ok"]:
        return report

    incident = ReconciliationIncident(
        portfolio_id=portfolio_id,
        owner_user_id=owner_user_id,
        kind="cash_or_quantity_mismatch",
        detail="Simulation reconciliation failed; mutations blocked",
        snapshot_json=report,
    )
    db.add(incident)
    db.flush()
    record_audit_event(
        db,
        actor_subject=actor_subject,
        action=AUDIT_RECON_BLOCK,
        resource_type="portfolio",
        resource_id=str(portfolio_id),
        metadata={"incident_id": str(incident.id), "report": report},
    )
    db.commit()
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="Portfolio reconciliation failed; trading is blocked until resolved",
    )
