"""Normalize provider prices onto internal listings."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from kyverance.market_data.dto import NormalizedDailyPrice, ProviderDailyPrice, ValidationIssue
from kyverance.market_data.models import ProviderInstrumentMapping


def build_symbol_map(db: Session, provider_id: UUID) -> dict[tuple[str, str], UUID]:
    rows = (
        db.query(ProviderInstrumentMapping)
        .filter(
            ProviderInstrumentMapping.provider_id == provider_id,
            ProviderInstrumentMapping.is_active.is_(True),
        )
        .all()
    )
    out: dict[tuple[str, str], UUID] = {}
    for r in rows:
        out[(r.provider_symbol.upper(), (r.provider_exchange_code or "US").upper())] = (
            r.instrument_listing_id
        )
    return out


def normalize_prices(
    prices: list[ProviderDailyPrice],
    *,
    symbol_map: dict[tuple[str, str], UUID],
) -> tuple[list[NormalizedDailyPrice], list[ValidationIssue]]:
    ok: list[NormalizedDailyPrice] = []
    issues: list[ValidationIssue] = []
    for p in prices:
        key = (p.provider_symbol.upper(), p.provider_exchange_code.upper())
        listing_id = symbol_map.get(key) or symbol_map.get((p.provider_symbol.upper(), "US"))
        if listing_id is None:
            issues.append(
                ValidationIssue(
                    error_type="unmapped_instrument",
                    message=f"No mapping for {p.provider_symbol}.{p.provider_exchange_code}",
                    provider_record_identifier=f"{p.provider_symbol}.{p.provider_exchange_code}",
                    raw_record=dict(p.raw) if p.raw else None,
                )
            )
            continue
        ok.append(
            NormalizedDailyPrice(
                instrument_listing_id=str(listing_id),
                trading_date=p.trading_date,
                open=p.open,
                high=p.high,
                low=p.low,
                close=p.close,
                adjusted_close=p.adjusted_close,
                volume=p.volume,
                currency_code=p.currency_code or "USD",
                provider_symbol=p.provider_symbol,
                provider_exchange_code=p.provider_exchange_code,
                source_updated_at=p.source_updated_at,
            )
        )
    return ok, issues
