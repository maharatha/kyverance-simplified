"""FIFO position and lot mutations for simulated fills."""

from __future__ import annotations

import uuid
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from kyverance.simulation.models import SimPosition, SimPositionLot
from kyverance.simulation.money import money, qty


def held_quantity(db: Session, portfolio_id: uuid.UUID, symbol: str) -> Decimal:
    pos = (
        db.query(SimPosition)
        .filter(SimPosition.portfolio_id == portfolio_id, SimPosition.symbol == symbol)
        .one_or_none()
    )
    return qty(pos.quantity) if pos is not None else qty("0")


def apply_buy(
    db: Session,
    *,
    portfolio_id: uuid.UUID,
    symbol: str,
    quantity: Decimal,
    price: Decimal,
    execution_id: uuid.UUID,
) -> SimPosition:
    quantity = qty(quantity)
    price = money(price)
    if quantity <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Buy quantity must be positive")

    pos = (
        db.query(SimPosition)
        .filter(SimPosition.portfolio_id == portfolio_id, SimPosition.symbol == symbol)
        .one_or_none()
    )
    if pos is None:
        pos = SimPosition(
            portfolio_id=portfolio_id,
            symbol=symbol,
            quantity=quantity,
            avg_cost=price,
        )
        db.add(pos)
    else:
        old_qty = qty(pos.quantity)
        new_qty = qty(old_qty + quantity)
        pos.avg_cost = money(((money(pos.avg_cost) * old_qty) + (price * quantity)) / new_qty)
        pos.quantity = new_qty

    db.add(
        SimPositionLot(
            portfolio_id=portfolio_id,
            symbol=symbol,
            quantity_remaining=quantity,
            unit_cost=price,
            execution_id=execution_id,
        )
    )
    db.flush()
    return pos


def apply_sell(
    db: Session,
    *,
    portfolio_id: uuid.UUID,
    symbol: str,
    quantity: Decimal,
) -> SimPosition | None:
    quantity = qty(quantity)
    if quantity <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Sell quantity must be positive")

    pos = (
        db.query(SimPosition)
        .filter(SimPosition.portfolio_id == portfolio_id, SimPosition.symbol == symbol)
        .one_or_none()
    )
    if pos is None or qty(pos.quantity) < quantity:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Insufficient holdings")

    remaining = quantity
    lots = (
        db.query(SimPositionLot)
        .filter(
            SimPositionLot.portfolio_id == portfolio_id,
            SimPositionLot.symbol == symbol,
            SimPositionLot.quantity_remaining > 0,
        )
        .order_by(SimPositionLot.opened_at.asc(), SimPositionLot.id.asc())
        .all()
    )
    for lot in lots:
        if remaining <= 0:
            break
        take = min(qty(lot.quantity_remaining), remaining)
        lot.quantity_remaining = qty(lot.quantity_remaining) - take
        remaining = qty(remaining - take)

    if remaining > qty("0"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Insufficient holdings")

    pos.quantity = qty(pos.quantity) - quantity
    if pos.quantity <= 0:
        db.delete(pos)
        db.flush()
        return None
    db.flush()
    return pos


def list_positions(db: Session, portfolio_id: uuid.UUID) -> list[SimPosition]:
    return (
        db.query(SimPosition)
        .filter(SimPosition.portfolio_id == portfolio_id)
        .order_by(SimPosition.symbol.asc())
        .all()
    )
