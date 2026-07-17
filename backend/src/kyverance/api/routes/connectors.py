from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from kyverance.auth.deps import require_authenticated
from kyverance.auth.models import AuthenticatedSubject
from kyverance.config import Settings, get_settings
from kyverance.connectors import service as connectors_service
from kyverance.connectors.schemas import (
    ConnectorsOverviewOut,
    DeletionRequestOut,
    PlaidConsentIn,
    PlaidExchangeIn,
    PlaidLinkTokenOut,
)
from kyverance.db.session import get_db

router = APIRouter(prefix="/connectors", tags=["connectors"])


@router.get("", response_model=ConnectorsOverviewOut)
def get_connectors(
    subject: Annotated[AuthenticatedSubject, Depends(require_authenticated)],
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> ConnectorsOverviewOut:
    return connectors_service.get_overview(db, subject, settings)


@router.post("/plaid/consent", response_model=ConnectorsOverviewOut)
def set_plaid_consent(
    body: PlaidConsentIn,
    subject: Annotated[AuthenticatedSubject, Depends(require_authenticated)],
    db: Annotated[Session, Depends(get_db)],
) -> ConnectorsOverviewOut:
    return connectors_service.set_plaid_consent(db, subject, granted=body.granted)


@router.post("/plaid/link-token", response_model=PlaidLinkTokenOut)
def create_plaid_link_token(
    subject: Annotated[AuthenticatedSubject, Depends(require_authenticated)],
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> PlaidLinkTokenOut:
    return connectors_service.create_link_token(db, subject, settings)


@router.post("/plaid/exchange", response_model=ConnectorsOverviewOut)
def exchange_plaid_token(
    body: PlaidExchangeIn,
    subject: Annotated[AuthenticatedSubject, Depends(require_authenticated)],
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> ConnectorsOverviewOut:
    return connectors_service.exchange_public_token(
        db,
        subject,
        public_token=body.public_token,
        provider_key=body.provider_key,
        settings=settings,
    )


@router.post("/plaid/fake-connect", response_model=ConnectorsOverviewOut)
def fake_connect(
    subject: Annotated[AuthenticatedSubject, Depends(require_authenticated)],
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> ConnectorsOverviewOut:
    """Local/test-only convenience path when Plaid credentials are unset."""
    return connectors_service.fake_connect_for_local(db, subject, settings)


@router.post("/connections/{connection_id}/refresh", response_model=ConnectorsOverviewOut)
def refresh_connection(
    connection_id: uuid.UUID,
    subject: Annotated[AuthenticatedSubject, Depends(require_authenticated)],
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> ConnectorsOverviewOut:
    return connectors_service.refresh_connection(db, subject, connection_id, settings)


@router.delete("/connections/{connection_id}", response_model=ConnectorsOverviewOut)
def disconnect_connection(
    connection_id: uuid.UUID,
    subject: Annotated[AuthenticatedSubject, Depends(require_authenticated)],
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> ConnectorsOverviewOut:
    return connectors_service.disconnect_connection(db, subject, connection_id, settings)


@router.post("/connections/{connection_id}/deletion-request", response_model=DeletionRequestOut)
def request_connection_deletion(
    connection_id: uuid.UUID,
    subject: Annotated[AuthenticatedSubject, Depends(require_authenticated)],
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> DeletionRequestOut:
    return connectors_service.request_deletion(db, subject, connection_id, settings)
