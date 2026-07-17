"""Portfolio + wallet creation/list/read services."""

from __future__ import annotations

import uuid
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from kyverance.audit.service import record_audit_event
from kyverance.auth.models import AuthenticatedSubject
from kyverance.portfolios.authorize import get_owned_portfolio, require_user_id
from kyverance.portfolios.models import Portfolio
from kyverance.portfolios.schemas import (
    LedgerEntryOut,
    PortfolioDetailOut,
    PortfolioListOut,
    PortfolioSummaryOut,
    WalletOut,
)
from kyverance.simulation.constants import (
    AUDIT_LEDGER_APPEND,
    AUDIT_PORTFOLIO_CREATE,
    FUNDING_BUCKET_COMPLIMENTARY,
    INITIAL_ALLOCATION_AMOUNT,
    INITIAL_ALLOCATION_SOURCE,
    PORTFOLIO_PROVENANCE_SIMULATED,
    PORTFOLIO_STATUS_ACTIVE,
    PORTFOLIO_VISIBILITY_PRIVATE,
    VIRTUAL_CURRENCY_CODE,
)
from kyverance.simulation.models import SimWallet, WalletLedgerEntry
from kyverance.simulation.money import money, money_str


def _wallet_out(wallet: SimWallet) -> WalletOut:
    return WalletOut(
        id=str(wallet.id),
        cash_balance=money_str(wallet.balance),
        complimentary_balance=money_str(wallet.complimentary_balance),
        currency_code=wallet.currency_code,
        version=int(wallet.version or 0),
    )


def _ledger_out(entry: WalletLedgerEntry) -> LedgerEntryOut:
    return LedgerEntryOut(
        id=str(entry.id),
        amount=money_str(entry.amount),
        currency_code=entry.currency_code,
        source_type=entry.source_type,
        funding_bucket=entry.funding_bucket,
        reason=entry.reason,
        actor=entry.actor,
        created_at=entry.created_at,
        idempotency_key=entry.idempotency_key,
    )


def _summary_out(portfolio: Portfolio) -> PortfolioSummaryOut:
    wallet = portfolio.wallet
    cash = money_str(wallet.balance) if wallet is not None else money_str("0")
    return PortfolioSummaryOut(
        id=str(portfolio.id),
        name=portfolio.name,
        description=portfolio.description,
        visibility=portfolio.visibility,
        provenance=portfolio.provenance,
        status=portfolio.status,
        currency_code=portfolio.currency_code,
        cash_balance=cash,
        created_at=portfolio.created_at,
        updated_at=portfolio.updated_at,
    )


def _detail_out(portfolio: Portfolio) -> PortfolioDetailOut:
    if portfolio.wallet is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Portfolio wallet is missing",
        )
    ledger = sorted(portfolio.wallet.ledger_entries, key=lambda e: (e.created_at, str(e.id)))
    summary = _summary_out(portfolio)
    return PortfolioDetailOut(
        **summary.model_dump(),
        wallet=_wallet_out(portfolio.wallet),
        ledger=[_ledger_out(entry) for entry in ledger],
    )


def ledger_sum(db: Session, wallet_id: uuid.UUID) -> Decimal:
    total = (
        db.query(func.coalesce(func.sum(WalletLedgerEntry.amount), 0))
        .filter(WalletLedgerEntry.wallet_id == wallet_id)
        .scalar()
    )
    return money(total)


def append_ledger(
    db: Session,
    *,
    wallet: SimWallet,
    amount: Decimal | str | int,
    source_type: str,
    idempotency_key: str | None,
    actor: str,
    reason: str | None = None,
    funding_bucket: str = FUNDING_BUCKET_COMPLIMENTARY,
    audit_actor: str | None = None,
    related_order_id: uuid.UUID | None = None,
) -> WalletLedgerEntry:
    """Append an immutable ledger entry and update wallet projections in the same unit of work."""
    amount = money(amount)
    if idempotency_key:
        existing = (
            db.query(WalletLedgerEntry)
            .filter(
                WalletLedgerEntry.wallet_id == wallet.id,
                WalletLedgerEntry.idempotency_key == idempotency_key,
            )
            .one_or_none()
        )
        if existing is not None:
            return existing

    entry = WalletLedgerEntry(
        wallet_id=wallet.id,
        portfolio_id=wallet.portfolio_id,
        owner_user_id=wallet.owner_user_id,
        amount=amount,
        currency_code=wallet.currency_code,
        source_type=source_type,
        funding_bucket=funding_bucket,
        idempotency_key=idempotency_key,
        reason=reason,
        actor=actor,
        related_order_id=related_order_id,
    )
    db.add(entry)
    wallet.balance = money(wallet.balance) + amount
    if funding_bucket == FUNDING_BUCKET_COMPLIMENTARY:
        wallet.complimentary_balance = money(wallet.complimentary_balance) + amount
    wallet.version = int(wallet.version or 0) + 1
    db.flush()

    record_audit_event(
        db,
        actor_subject=audit_actor or actor,
        action=AUDIT_LEDGER_APPEND,
        resource_type="wallet_ledger_entry",
        resource_id=str(entry.id),
        metadata={
            "wallet_id": str(wallet.id),
            "portfolio_id": str(wallet.portfolio_id),
            "amount": money_str(amount),
            "source_type": source_type,
            "funding_bucket": funding_bucket,
        },
    )
    return entry


def create_portfolio(
    db: Session,
    subject: AuthenticatedSubject,
    *,
    name: str,
    description: str | None = None,
    idempotency_key: str | None = None,
) -> PortfolioDetailOut:
    user_id = require_user_id(subject)
    cleaned_name = name.strip()
    if not cleaned_name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Portfolio name is required")
    cleaned_description = description.strip() if description and description.strip() else None
    cleaned_key = idempotency_key.strip() if idempotency_key and idempotency_key.strip() else None

    if cleaned_key:
        existing = (
            db.query(Portfolio)
            .filter(
                Portfolio.owner_user_id == user_id,
                Portfolio.creation_idempotency_key == cleaned_key,
            )
            .one_or_none()
        )
        if existing is not None:
            return _detail_out(existing)

    portfolio = Portfolio(
        owner_user_id=user_id,
        name=cleaned_name,
        description=cleaned_description,
        visibility=PORTFOLIO_VISIBILITY_PRIVATE,
        provenance=PORTFOLIO_PROVENANCE_SIMULATED,
        status=PORTFOLIO_STATUS_ACTIVE,
        currency_code=VIRTUAL_CURRENCY_CODE,
        creation_idempotency_key=cleaned_key,
    )
    db.add(portfolio)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        if cleaned_key:
            existing = (
                db.query(Portfolio)
                .filter(
                    Portfolio.owner_user_id == user_id,
                    Portfolio.creation_idempotency_key == cleaned_key,
                )
                .one_or_none()
            )
            if existing is not None:
                return _detail_out(existing)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Unable to create portfolio",
        ) from exc

    wallet = SimWallet(
        portfolio_id=portfolio.id,
        owner_user_id=user_id,
        currency_code=VIRTUAL_CURRENCY_CODE,
        balance=money("0"),
        complimentary_balance=money("0"),
        version=0,
    )
    db.add(wallet)
    db.flush()

    append_ledger(
        db,
        wallet=wallet,
        amount=INITIAL_ALLOCATION_AMOUNT,
        source_type=INITIAL_ALLOCATION_SOURCE,
        idempotency_key=f"initial:{portfolio.id}",
        actor="system",
        reason="Complimentary practice currency (~USD 1,000 equivalent)",
        funding_bucket=FUNDING_BUCKET_COMPLIMENTARY,
        audit_actor=subject.subject,
    )

    record_audit_event(
        db,
        actor_subject=subject.subject,
        action=AUDIT_PORTFOLIO_CREATE,
        resource_type="portfolio",
        resource_id=str(portfolio.id),
        metadata={
            "name": portfolio.name,
            "currency_code": portfolio.currency_code,
            "initial_allocation": money_str(INITIAL_ALLOCATION_AMOUNT),
            "idempotency_key": cleaned_key,
        },
    )
    db.commit()
    db.refresh(portfolio)
    return _detail_out(portfolio)


def list_portfolios(db: Session, subject: AuthenticatedSubject) -> PortfolioListOut:
    user_id = require_user_id(subject)
    portfolios = (
        db.query(Portfolio)
        .filter(Portfolio.owner_user_id == user_id)
        .order_by(Portfolio.created_at.desc())
        .all()
    )
    return PortfolioListOut(
        portfolios=[_summary_out(p) for p in portfolios],
        empty_state="empty" if not portfolios else "populated",
    )


def get_portfolio(
    db: Session,
    subject: AuthenticatedSubject,
    portfolio_id: uuid.UUID,
) -> PortfolioDetailOut:
    portfolio = get_owned_portfolio(db, subject, portfolio_id)
    return _detail_out(portfolio)
