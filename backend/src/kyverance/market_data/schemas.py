"""API schemas for internal market-data reads."""

from __future__ import annotations

from pydantic import BaseModel, Field


class LatestPriceOut(BaseModel):
    instrumentListingId: str
    instrumentId: str
    ticker: str
    exchange: str
    currency: str
    tradingDate: str
    open: str
    high: str
    low: str
    close: str
    adjustedClose: str | None = None
    volume: int
    dataStatus: str
    dataVersion: int
    updatedAt: str
    isStale: bool
    canonicalName: str | None = None
    providerId: str | None = None
    dataAsOf: str | None = None
    availability: str | None = None


class HistoryPointOut(BaseModel):
    tradingDate: str
    open: str
    high: str
    low: str
    close: str
    adjustedClose: str | None = None
    volume: int
    dataVersion: int
    dataStatus: str | None = None
    providerId: str | None = None


class HistoryOut(BaseModel):
    instrumentListingId: str
    from_: str = Field(alias="from")
    to: str
    points: list[HistoryPointOut]
    dataVersion: int

    model_config = {"populate_by_name": True}


class SearchResultOut(BaseModel):
    instrumentListingId: str
    symbol: str
    name: str
    exchange: str
    type: str
    price: str | None = None


class SearchOut(BaseModel):
    results: list[SearchResultOut]
