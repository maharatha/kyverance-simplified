from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from kyverance.auth.deps import require_authenticated
from kyverance.auth.models import AuthenticatedSubject
from kyverance.db.session import get_db
from kyverance.portfolios import service as portfolios_service
from kyverance.portfolios.schemas import PortfolioCreateIn, PortfolioDetailOut, PortfolioListOut

router = APIRouter(prefix="/portfolios", tags=["portfolios"])


@router.get("", response_model=PortfolioListOut)
def list_portfolios(
    subject: Annotated[AuthenticatedSubject, Depends(require_authenticated)],
    db: Annotated[Session, Depends(get_db)],
) -> PortfolioListOut:
    return portfolios_service.list_portfolios(db, subject)


@router.post("", response_model=PortfolioDetailOut, status_code=201)
def create_portfolio(
    body: PortfolioCreateIn,
    subject: Annotated[AuthenticatedSubject, Depends(require_authenticated)],
    db: Annotated[Session, Depends(get_db)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> PortfolioDetailOut:
    return portfolios_service.create_portfolio(
        db,
        subject,
        name=body.name,
        description=body.description,
        idempotency_key=idempotency_key,
    )


@router.get("/{portfolio_id}", response_model=PortfolioDetailOut)
def get_portfolio(
    portfolio_id: uuid.UUID,
    subject: Annotated[AuthenticatedSubject, Depends(require_authenticated)],
    db: Annotated[Session, Depends(get_db)],
) -> PortfolioDetailOut:
    return portfolios_service.get_portfolio(db, subject, portfolio_id)
