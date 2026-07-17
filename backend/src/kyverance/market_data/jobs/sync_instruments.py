"""Sync instruments / listings / provider mappings."""

from __future__ import annotations

import logging
from uuid import uuid4

from sqlalchemy.orm import Session

from kyverance.market_data.models import (
    DataProvider,
    Instrument,
    InstrumentListing,
    MarketExchange,
    ProviderInstrumentMapping,
)
from kyverance.market_data.providers.registry import get_market_data_provider

logger = logging.getLogger(__name__)


async def sync_instruments(
    db: Session, *, exchange_canonical: str = "XNAS", limit: int | None = None
) -> dict:
    provider = get_market_data_provider()
    dp = db.query(DataProvider).filter(DataProvider.code == provider.code).one()
    fallback = (
        db.query(MarketExchange)
        .filter(MarketExchange.canonical_code == exchange_canonical.upper())
        .one_or_none()
    )
    if not fallback:
        raise RuntimeError(f"Unknown exchange {exchange_canonical}")

    remote = await provider.get_instruments("US")
    if limit and limit > 0:
        remote = remote[:limit]

    listings = db.query(InstrumentListing).filter(InstrumentListing.is_active.is_(True)).all()
    listing_by_ex_ticker: dict[tuple[object, str], InstrumentListing] = {
        (row.exchange_id, row.ticker.upper()): row for row in listings
    }
    listing_by_ticker: dict[str, InstrumentListing] = {}
    for row in listings:
        listing_by_ticker.setdefault(row.ticker.upper(), row)

    mappings = (
        db.query(ProviderInstrumentMapping)
        .filter(
            ProviderInstrumentMapping.provider_id == dp.id,
            ProviderInstrumentMapping.provider_exchange_code == "US",
            ProviderInstrumentMapping.is_active.is_(True),
        )
        .all()
    )
    mapping_by_symbol = {row.provider_symbol.upper(): row for row in mappings}

    created_instruments = 0
    created_listings = 0
    created_mappings = 0

    for pi in remote:
        ticker = pi.provider_symbol.upper()
        exchange = fallback
        listing = listing_by_ex_ticker.get((exchange.id, ticker))
        if listing is None:
            sibling = listing_by_ticker.get(ticker)
            if sibling:
                instrument_id = sibling.instrument_id
            else:
                inst = Instrument(
                    id=uuid4(),
                    instrument_type=pi.instrument_type,
                    canonical_name=pi.name,
                    primary_exchange_id=exchange.id,
                    primary_currency_code=pi.currency_code or "USD",
                    isin=pi.isin,
                    is_active=True,
                )
                db.add(inst)
                instrument_id = inst.id
                created_instruments += 1

            listing = InstrumentListing(
                id=uuid4(),
                instrument_id=instrument_id,
                exchange_id=exchange.id,
                ticker=ticker,
                currency_code=pi.currency_code or "USD",
                is_primary=True,
                is_active=True,
            )
            db.add(listing)
            listing_by_ex_ticker[(exchange.id, ticker)] = listing
            listing_by_ticker.setdefault(ticker, listing)
            created_listings += 1

        if ticker not in mapping_by_symbol:
            mapping = ProviderInstrumentMapping(
                id=uuid4(),
                provider_id=dp.id,
                instrument_listing_id=listing.id,
                provider_symbol=ticker,
                provider_exchange_code="US",
                is_active=True,
                provider_metadata_json=dict(pi.metadata) if pi.metadata else None,
            )
            db.add(mapping)
            mapping_by_symbol[ticker] = mapping
            created_mappings += 1

    db.commit()
    logger.info(
        "market_data.sync_instruments provider=%s instruments=%s listings=%s mappings=%s",
        provider.code,
        created_instruments,
        created_listings,
        created_mappings,
    )
    return {
        "provider": provider.code,
        "created_instruments": created_instruments,
        "created_listings": created_listings,
        "created_mappings": created_mappings,
        "remote": len(remote),
    }
