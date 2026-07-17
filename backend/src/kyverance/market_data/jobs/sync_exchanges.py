"""Sync provider exchanges into canonical market_exchanges."""

from __future__ import annotations

import logging
from uuid import uuid4

from sqlalchemy.orm import Session

from kyverance.market_data.models import DataProvider, MarketExchange
from kyverance.market_data.providers.registry import get_market_data_provider

logger = logging.getLogger(__name__)

US_PROVIDER_TO_CANONICAL = {
    "US": [("XNYS", "New York Stock Exchange"), ("XNAS", "NASDAQ")],
}


async def sync_exchanges(db: Session) -> dict:
    provider = get_market_data_provider()
    dp = db.query(DataProvider).filter(DataProvider.code == provider.code).one_or_none()
    if not dp:
        dp = DataProvider(
            id=uuid4(), code=provider.code, name=provider.code, provider_type="eod", is_active=True
        )
        db.add(dp)
        db.flush()

    remote = await provider.get_exchanges()
    created = 0
    for pe in remote:
        mapped = US_PROVIDER_TO_CANONICAL.get(pe.provider_code.upper())
        if mapped:
            for mic, name in mapped:
                existing = db.query(MarketExchange).filter(MarketExchange.mic_code == mic).one_or_none()
                if existing:
                    continue
                db.add(
                    MarketExchange(
                        id=uuid4(),
                        mic_code=mic,
                        canonical_code=mic,
                        name=name,
                        country_code=pe.country_code or "US",
                        currency_code=pe.currency_code or "USD",
                        timezone=pe.timezone or "America/New_York",
                    )
                )
                created += 1
        else:
            code = pe.provider_code.upper()[:16]
            existing = (
                db.query(MarketExchange).filter(MarketExchange.canonical_code == code).one_or_none()
            )
            if existing:
                continue
            db.add(
                MarketExchange(
                    id=uuid4(),
                    mic_code=pe.mic_hint or code,
                    canonical_code=code,
                    name=pe.name,
                    country_code=pe.country_code or "XX",
                    currency_code=pe.currency_code or "USD",
                    timezone=pe.timezone or "UTC",
                    is_active=False,
                )
            )
            created += 1
            logger.info("market_data.exchange.unknown code=%s", code)

    db.commit()
    return {"provider": provider.code, "created": created, "remote": len(remote)}
