"""Simulation domain constants for wallet/ledger and order loop."""

from __future__ import annotations

from decimal import Decimal

VIRTUAL_CURRENCY_CODE = "VUSD"
INITIAL_ALLOCATION_AMOUNT = Decimal("1000.0000")
INITIAL_ALLOCATION_SOURCE = "INITIAL_ALLOCATION"
FUNDING_BUCKET_COMPLIMENTARY = "complimentary"

PORTFOLIO_VISIBILITY_PRIVATE = "private"
PORTFOLIO_PROVENANCE_SIMULATED = "simulated"
PORTFOLIO_STATUS_ACTIVE = "active"

AUDIT_PORTFOLIO_CREATE = "portfolio.create"
AUDIT_LEDGER_APPEND = "wallet.ledger.append"
AUDIT_ORDER_PREVIEW = "order.preview"
AUDIT_ORDER_CONFIRM = "order.confirm"
AUDIT_RECON_BLOCK = "simulation.reconciliation.block"

SOURCE_ORDER_DEBIT = "ORDER_EXECUTION_DEBIT"
SOURCE_SALE_PROCEEDS = "SALE_PROCEEDS"

SLIPPAGE_BPS = Decimal("5")
FEE_AMOUNT = Decimal("0.0000")
PREVIEW_TTL_SECONDS = 60
QUOTE_MAX_AGE_SECONDS = 120

EXECUTION_POLICY = "market_us_equity_simulated"
DATA_MODE_FIXTURE = "fixture"
FRESHNESS_FRESH = "fresh"
FRESHNESS_STALE = "stale"
FRESHNESS_UNAVAILABLE = "unavailable"

ORDER_STATUS_EXECUTED = "EXECUTED"
ORDER_STATUS_REJECTED = "REJECTED"
PREVIEW_STATUS_OPEN = "open"
PREVIEW_STATUS_CONSUMED = "consumed"
PREVIEW_STATUS_EXPIRED = "expired"

SIDE_BUY = "buy"
SIDE_SELL = "sell"

DISCLOSURE_SIMULATED = (
    "Simulated order only. No real trade is sent to a broker or exchange. "
    "Virtual currency has no cash value."
)

# Deterministic fixture quotes (USD marks) for local/test — never live market data.
FIXTURE_QUOTES: dict[str, Decimal] = {
    "AAPL": Decimal("190.0000"),
    "MSFT": Decimal("420.0000"),
    "GOOGL": Decimal("175.0000"),
    "AMZN": Decimal("185.0000"),
    "NVDA": Decimal("120.0000"),
    "META": Decimal("500.0000"),
    "TSLA": Decimal("250.0000"),
    "SPY": Decimal("520.0000"),
    "QQQ": Decimal("450.0000"),
    "VTI": Decimal("260.0000"),
}
