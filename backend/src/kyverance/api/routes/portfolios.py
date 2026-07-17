from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from kyverance.auth.deps import require_authenticated
from kyverance.auth.models import AuthenticatedSubject
from kyverance.db.session import get_db
from kyverance.portfolios import service as portfolios_service
from kyverance.portfolios import versions as versions_service
from kyverance.portfolios.schemas import (
    ForkCreateIn,
    PortfolioCreateIn,
    PortfolioDetailOut,
    PortfolioListOut,
    PortfolioPatchIn,
    PortfolioVersionCreateIn,
    PortfolioVersionListOut,
    PortfolioVersionOut,
    PortfolioVersionPublishIn,
)

router = APIRouter(prefix="/portfolios", tags=["portfolios"])
versions_router = APIRouter(prefix="/portfolio-versions", tags=["portfolio-versions"])


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
        thesis=body.thesis,
        agent_config_ref=body.agent_config_ref,
        idempotency_key=idempotency_key,
    )


@router.get("/{portfolio_id}", response_model=PortfolioDetailOut)
def get_portfolio(
    portfolio_id: uuid.UUID,
    subject: Annotated[AuthenticatedSubject, Depends(require_authenticated)],
    db: Annotated[Session, Depends(get_db)],
) -> PortfolioDetailOut:
    return portfolios_service.get_portfolio(db, subject, portfolio_id)


@router.patch("/{portfolio_id}", response_model=PortfolioDetailOut)
def patch_portfolio(
    portfolio_id: uuid.UUID,
    body: PortfolioPatchIn,
    subject: Annotated[AuthenticatedSubject, Depends(require_authenticated)],
    db: Annotated[Session, Depends(get_db)],
) -> PortfolioDetailOut:
    return portfolios_service.patch_portfolio(
        db,
        subject,
        portfolio_id,
        name=body.name,
        description=body.description,
        thesis=body.thesis,
        agent_config_ref=body.agent_config_ref,
    )


@router.get("/{portfolio_id}/versions", response_model=PortfolioVersionListOut)
def list_versions(
    portfolio_id: uuid.UUID,
    subject: Annotated[AuthenticatedSubject, Depends(require_authenticated)],
    db: Annotated[Session, Depends(get_db)],
) -> PortfolioVersionListOut:
    return versions_service.list_versions(db, subject, portfolio_id)


@router.post("/{portfolio_id}/versions", response_model=PortfolioVersionOut, status_code=201)
def create_version(
    portfolio_id: uuid.UUID,
    subject: Annotated[AuthenticatedSubject, Depends(require_authenticated)],
    db: Annotated[Session, Depends(get_db)],
    body: PortfolioVersionCreateIn | None = None,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> PortfolioVersionOut:
    _ = body  # Snapshot is taken from live portfolio state.
    return versions_service.create_version(
        db,
        subject,
        portfolio_id,
        idempotency_key=idempotency_key,
    )


@router.get("/{portfolio_id}/versions/{version_id}", response_model=PortfolioVersionOut)
def get_owned_version(
    portfolio_id: uuid.UUID,
    version_id: uuid.UUID,
    subject: Annotated[AuthenticatedSubject, Depends(require_authenticated)],
    db: Annotated[Session, Depends(get_db)],
) -> PortfolioVersionOut:
    return versions_service.get_owned_portfolio_version(db, subject, portfolio_id, version_id)


@router.post(
    "/{portfolio_id}/versions/{version_id}/publish",
    response_model=PortfolioVersionOut,
)
def publish_version(
    portfolio_id: uuid.UUID,
    version_id: uuid.UUID,
    body: PortfolioVersionPublishIn,
    subject: Annotated[AuthenticatedSubject, Depends(require_authenticated)],
    db: Annotated[Session, Depends(get_db)],
) -> PortfolioVersionOut:
    return versions_service.publish_version(db, subject, portfolio_id, version_id, body)


@versions_router.get("/{version_id}", response_model=PortfolioVersionOut)
def get_version(
    version_id: uuid.UUID,
    subject: Annotated[AuthenticatedSubject, Depends(require_authenticated)],
    db: Annotated[Session, Depends(get_db)],
) -> PortfolioVersionOut:
    return versions_service.get_version(db, subject, version_id)


@versions_router.post("/{version_id}/fork", response_model=PortfolioDetailOut, status_code=201)
def fork_version(
    version_id: uuid.UUID,
    subject: Annotated[AuthenticatedSubject, Depends(require_authenticated)],
    db: Annotated[Session, Depends(get_db)],
    body: ForkCreateIn | None = None,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> PortfolioDetailOut:
    return versions_service.fork_version(
        db,
        subject,
        version_id,
        body,
        idempotency_key=idempotency_key,
    )
