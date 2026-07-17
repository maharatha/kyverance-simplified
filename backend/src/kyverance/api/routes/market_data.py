"""Customer-facing market-data APIs — Postgres only; never call providers."""

from __future__ import annotations

from datetime import date
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from kyverance.auth.deps import require_authenticated
from kyverance.auth.models import AuthenticatedSubject
from kyverance.config import get_settings
from kyverance.db.session import get_db
from kyverance.market_data import service as market_service
from kyverance.market_data.schemas import HistoryOut, LatestPriceOut, SearchOut
from kyverance.market_data.service import InternalDataUnavailable

router = APIRouter(prefix="/market-data", tags=["market-data"])


def _unavailable(exc: InternalDataUnavailable) -> HTTPException:
    return HTTPException(
        status_code=503,
        detail={"code": "internal_data_unavailable", "message": str(exc)},
    )


def _require_engine() -> None:
    if not get_settings().market_data_engine_enabled:
        raise HTTPException(status_code=503, detail="market_data_disabled")


@router.get("/exchanges/{exchange_code}/symbols/{ticker}/latest", response_model=LatestPriceOut)
def latest_by_symbol(
    exchange_code: str,
    ticker: str,
    db: Annotated[Session, Depends(get_db)],
    _subject: Annotated[AuthenticatedSubject, Depends(require_authenticated)],
) -> dict[str, Any]:
    _require_engine()
    try:
        return market_service.get_latest_by_symbol(db, exchange_code, ticker)
    except InternalDataUnavailable as exc:
        raise _unavailable(exc) from exc


@router.get("/instruments/{instrument_listing_id}/latest", response_model=LatestPriceOut)
def latest_by_id(
    instrument_listing_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    _subject: Annotated[AuthenticatedSubject, Depends(require_authenticated)],
) -> dict[str, Any]:
    _require_engine()
    try:
        return market_service.get_latest_by_listing_id(db, instrument_listing_id)
    except InternalDataUnavailable as exc:
        raise _unavailable(exc) from exc


@router.get("/exchanges/{exchange_code}/symbols/{ticker}/history", response_model=HistoryOut)
def history_by_symbol(
    exchange_code: str,
    ticker: str,
    db: Annotated[Session, Depends(get_db)],
    _subject: Annotated[AuthenticatedSubject, Depends(require_authenticated)],
    from_date: date = Query(alias="from"),
    to_date: date = Query(alias="to"),
) -> dict[str, Any]:
    _require_engine()
    try:
        return market_service.get_history_by_symbol(
            db, exchange_code, ticker, from_date=from_date, to_date=to_date
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except InternalDataUnavailable as exc:
        raise _unavailable(exc) from exc


@router.get("/instruments/{instrument_listing_id}/history", response_model=HistoryOut)
def history_by_id(
    instrument_listing_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    _subject: Annotated[AuthenticatedSubject, Depends(require_authenticated)],
    from_date: date = Query(alias="from"),
    to_date: date = Query(alias="to"),
) -> dict[str, Any]:
    _require_engine()
    try:
        return market_service.get_history(
            db, instrument_listing_id, from_date=from_date, to_date=to_date
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except InternalDataUnavailable as exc:
        raise _unavailable(exc) from exc


@router.get("/search", response_model=SearchOut)
def search(
    db: Annotated[Session, Depends(get_db)],
    _subject: Annotated[AuthenticatedSubject, Depends(require_authenticated)],
    q: str = Query(min_length=1, max_length=64),
) -> dict[str, Any]:
    _require_engine()
    return {"results": market_service.search_listings(db, q)}
