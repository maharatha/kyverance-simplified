from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from kyverance.auth.deps import require_authenticated
from kyverance.auth.models import AuthenticatedSubject
from kyverance.db.session import get_db
from kyverance.simulation import trading as trading_svc
from kyverance.simulation.schemas import (
    ActivityListOut,
    OrderConfirmIn,
    OrderPreviewIn,
    OrderPreviewOut,
    OrderReceiptOut,
    PositionsListOut,
    ReconciliationOut,
)

router = APIRouter(prefix="/portfolios/{portfolio_id}", tags=["orders"])


@router.post("/orders/preview", response_model=OrderPreviewOut)
def preview_order(
    portfolio_id: uuid.UUID,
    body: OrderPreviewIn,
    subject: Annotated[AuthenticatedSubject, Depends(require_authenticated)],
    db: Annotated[Session, Depends(get_db)],
) -> OrderPreviewOut:
    return trading_svc.preview_order(db, subject, portfolio_id, body)


@router.post("/orders/confirm", response_model=OrderReceiptOut)
def confirm_order(
    portfolio_id: uuid.UUID,
    body: OrderConfirmIn,
    subject: Annotated[AuthenticatedSubject, Depends(require_authenticated)],
    db: Annotated[Session, Depends(get_db)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> OrderReceiptOut:
    return trading_svc.confirm_order(
        db,
        subject,
        portfolio_id,
        body,
        idempotency_key=idempotency_key,
    )


@router.get("/orders/{order_id}/receipt", response_model=OrderReceiptOut)
def get_receipt(
    portfolio_id: uuid.UUID,
    order_id: uuid.UUID,
    subject: Annotated[AuthenticatedSubject, Depends(require_authenticated)],
    db: Annotated[Session, Depends(get_db)],
) -> OrderReceiptOut:
    return trading_svc.get_receipt(db, subject, portfolio_id, order_id)


@router.get("/activity", response_model=ActivityListOut)
def list_activity(
    portfolio_id: uuid.UUID,
    subject: Annotated[AuthenticatedSubject, Depends(require_authenticated)],
    db: Annotated[Session, Depends(get_db)],
) -> ActivityListOut:
    return trading_svc.list_activity(db, subject, portfolio_id)


@router.get("/positions", response_model=PositionsListOut)
def get_positions(
    portfolio_id: uuid.UUID,
    subject: Annotated[AuthenticatedSubject, Depends(require_authenticated)],
    db: Annotated[Session, Depends(get_db)],
) -> PositionsListOut:
    return trading_svc.get_positions(db, subject, portfolio_id)


@router.get("/reconciliation", response_model=ReconciliationOut)
def get_reconciliation(
    portfolio_id: uuid.UUID,
    subject: Annotated[AuthenticatedSubject, Depends(require_authenticated)],
    db: Annotated[Session, Depends(get_db)],
) -> ReconciliationOut:
    return trading_svc.get_reconciliation(db, subject, portfolio_id)
