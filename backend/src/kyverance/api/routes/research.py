"""Research API routes — read published research; never deep-generate on request path."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from kyverance.auth.deps import require_authenticated
from kyverance.auth.models import AuthenticatedSubject
from kyverance.config import Settings, get_settings
from kyverance.db.session import get_db
from kyverance.research.service import get_research_for_symbol

router = APIRouter(prefix="/research", tags=["research"])


@router.get("/securities/{symbol}")
def get_security_research(
    symbol: str,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    _subject: Annotated[AuthenticatedSubject, Depends(require_authenticated)],
) -> dict[str, Any]:
    if not settings.research_engine_enabled:
        raise HTTPException(status_code=503, detail="research_disabled")

    payload, status_hint = get_research_for_symbol(db, symbol, settings=settings)
    if payload is None:
        raise HTTPException(status_code=404, detail="research_unavailable")
    response.status_code = status_hint
    return payload
