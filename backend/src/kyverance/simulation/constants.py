"""Simulation domain constants for SIM-01 wallet/ledger."""

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
