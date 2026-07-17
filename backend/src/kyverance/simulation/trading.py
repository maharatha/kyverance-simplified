"""Deterministic simulated market-order preview and confirmation."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from kyverance.audit.service import record_audit_event
from kyverance.auth.models import AuthenticatedSubject
from kyverance.portfolios.authorize import get_owned_portfolio, require_user_id
from kyverance.portfolios.service import append_ledger
from kyverance.simulation.constants import (
    AUDIT_ORDER_CONFIRM,
    AUDIT_ORDER_PREVIEW,
    DISCLOSURE_SIMULATED,
    EXECUTION_POLICY,
    FEE_AMOUNT,
    ORDER_STATUS_EXECUTED,
    PREVIEW_STATUS_CONSUMED,
    PREVIEW_STATUS_EXPIRED,
    PREVIEW_STATUS_OPEN,
    PREVIEW_TTL_SECONDS,
    SIDE_BUY,
    SIDE_SELL,
    SLIPPAGE_BPS,
    SOURCE_ORDER_DEBIT,
    SOURCE_SALE_PROCEEDS,
)
from kyverance.simulation.models import (
    OrderPreview,
    OrderReceipt,
    SimExecution,
    SimOrder,
    SimWallet,
)
from kyverance.simulation.money import money, money_str, qty, qty_str
from kyverance.simulation.positions import apply_buy, apply_sell, held_quantity, list_positions
from kyverance.simulation.quotes import fetch_quote, require_fresh_quote
from kyverance.simulation.reconcile import reconcile_portfolio, require_reconciled
from kyverance.simulation.schemas import (
    ActivityItemOut,
    ActivityListOut,
    OrderConfirmIn,
    OrderPreviewIn,
    OrderPreviewOut,
    OrderReceiptOut,
    PositionOut,
    PositionsListOut,
    QuoteMetaOut,
    ReconciliationOut,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)

def _as_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)




def _fingerprint(*, symbol: str, side: str, quantity: str | None, notional: str | None) -> str:
    payload = {
        "symbol": symbol,
        "side": side,
        "quantity": quantity,
        "notional": notional,
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _require_wallet(portfolio) -> SimWallet:
    if portfolio.wallet is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Portfolio wallet is missing",
        )
    return portfolio.wallet


def _quote_meta(preview: OrderPreview) -> QuoteMetaOut:
    return QuoteMetaOut(
        quote_id=preview.quote_id,
        quote_as_of=preview.quote_as_of,
        quote_received_at=preview.quote_received_at,
        provider=preview.provider,
        freshness_label=preview.freshness_label,
        data_mode=preview.data_mode,
        execution_policy=preview.execution_policy,
    )


def _preview_out(preview: OrderPreview) -> OrderPreviewOut:
    return OrderPreviewOut(
        preview_id=str(preview.id),
        portfolio_id=str(preview.portfolio_id),
        wallet_id=str(preview.wallet_id),
        symbol=preview.symbol,
        side=preview.side,
        quantity=qty_str(preview.quantity),
        notional=money_str(preview.notional),
        quote_price=money_str(preview.quote_price),
        execution_price=money_str(preview.execution_price),
        slippage_bps=money_str(preview.slippage_bps),
        fee=money_str(preview.fee),
        cash_after=money_str(preview.cash_after),
        warnings=list(preview.warnings_json or []),
        expires_at=preview.expires_at,
        status=preview.status,
        quote=_quote_meta(preview),
        disclosure=DISCLOSURE_SIMULATED,
    )


def _receipt_out(receipt: OrderReceipt) -> OrderReceiptOut:
    return OrderReceiptOut.model_validate(dict(receipt.payload_json))


def preview_order(
    db: Session,
    subject: AuthenticatedSubject,
    portfolio_id: uuid.UUID,
    body: OrderPreviewIn,
) -> OrderPreviewOut:
    user_id = require_user_id(subject)
    portfolio = get_owned_portfolio(db, subject, portfolio_id)
    wallet = _require_wallet(portfolio)
    require_reconciled(
        db,
        wallet=wallet,
        portfolio_id=portfolio.id,
        owner_user_id=user_id,
        actor_subject=subject.subject,
    )

    symbol = body.symbol.upper().strip()
    side = body.side.lower().strip()
    if side not in (SIDE_BUY, SIDE_SELL):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="side must be buy or sell")
    if (body.quantity is None) == (body.notional is None):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide exactly one of quantity or notional",
        )

    quote = fetch_quote(symbol)
    require_fresh_quote(quote)

    slip = money(quote.price * SLIPPAGE_BPS / Decimal("10000"))
    exec_price = money(quote.price + slip if side == SIDE_BUY else quote.price - slip)
    fee = money(FEE_AMOUNT)

    if body.notional is not None:
        notional = money(body.notional)
        if notional <= 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="notional must be positive")
        quantity = qty(notional / exec_price)
    else:
        assert body.quantity is not None
        quantity = qty(body.quantity)
        if quantity <= 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="quantity must be positive")
        notional = money(quantity * exec_price)

    warnings: list[str] = []
    held = held_quantity(db, portfolio.id, symbol)
    if side == SIDE_BUY and notional > money(wallet.balance):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Insufficient buying power")
    if side == SIDE_SELL:
        if held <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No holdings in {symbol}",
            )
        if quantity > held:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Insufficient holdings")

    cash_after = (
        money(wallet.balance) - notional - fee if side == SIDE_BUY else money(wallet.balance) + notional - fee
    )
    fp = _fingerprint(
        symbol=symbol,
        side=side,
        quantity=qty_str(quantity) if body.quantity is not None else None,
        notional=money_str(body.notional) if body.notional is not None else None,
    )
    now = _now()
    preview = OrderPreview(
        portfolio_id=portfolio.id,
        wallet_id=wallet.id,
        owner_user_id=user_id,
        symbol=symbol,
        side=side,
        quantity=quantity,
        notional=notional,
        quote_price=quote.price,
        execution_price=exec_price,
        slippage_bps=SLIPPAGE_BPS,
        fee=fee,
        quote_id=quote.quote_id,
        quote_as_of=quote.as_of,
        quote_received_at=quote.received_at,
        provider=quote.provider,
        freshness_label=quote.freshness_label,
        data_mode=quote.data_mode,
        execution_policy=EXECUTION_POLICY,
        cash_after=cash_after,
        warnings_json=warnings,
        request_fingerprint=fp,
        status=PREVIEW_STATUS_OPEN,
        expires_at=now + timedelta(seconds=PREVIEW_TTL_SECONDS),
    )
    db.add(preview)
    db.flush()
    record_audit_event(
        db,
        actor_subject=subject.subject,
        action=AUDIT_ORDER_PREVIEW,
        resource_type="order_preview",
        resource_id=str(preview.id),
        metadata={
            "portfolio_id": str(portfolio.id),
            "symbol": symbol,
            "side": side,
            "quantity": qty_str(quantity),
            "notional": money_str(notional),
            "quote_id": quote.quote_id,
            "data_mode": quote.data_mode,
            "freshness_label": quote.freshness_label,
        },
    )
    db.commit()
    db.refresh(preview)
    return _preview_out(preview)


def confirm_order(
    db: Session,
    subject: AuthenticatedSubject,
    portfolio_id: uuid.UUID,
    body: OrderConfirmIn,
    *,
    idempotency_key: str | None,
) -> OrderReceiptOut:
    if not idempotency_key or len(idempotency_key.strip()) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Idempotency-Key header required (min 8 characters)",
        )
    cleaned_key = idempotency_key.strip()
    user_id = require_user_id(subject)
    portfolio = get_owned_portfolio(db, subject, portfolio_id)
    wallet = _require_wallet(portfolio)

    existing = (
        db.query(SimOrder)
        .filter(SimOrder.owner_user_id == user_id, SimOrder.idempotency_key == cleaned_key)
        .one_or_none()
    )
    if existing is not None:
        if str(existing.portfolio_id) != str(portfolio_id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Idempotency-Key already used for a different portfolio",
            )
        if str(existing.preview_id) != body.preview_id.strip():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Idempotency-Key already used with a different preview",
            )
        if existing.receipt is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Prior order is missing receipt",
            )
        return _receipt_out(existing.receipt)

    require_reconciled(
        db,
        wallet=wallet,
        portfolio_id=portfolio.id,
        owner_user_id=user_id,
        actor_subject=subject.subject,
    )

    try:
        preview_uuid = uuid.UUID(body.preview_id.strip())
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid preview_id") from exc

    preview = (
        db.query(OrderPreview)
        .filter(
            OrderPreview.id == preview_uuid,
            OrderPreview.portfolio_id == portfolio.id,
            OrderPreview.owner_user_id == user_id,
        )
        .one_or_none()
    )
    if preview is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Preview not found")

    now = _now()
    if preview.status == PREVIEW_STATUS_CONSUMED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Preview already consumed")
    if preview.status == PREVIEW_STATUS_EXPIRED or _as_utc(preview.expires_at) <= now:
        preview.status = PREVIEW_STATUS_EXPIRED
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Preview expired — request a new preview",
        )
    if preview.status != PREVIEW_STATUS_OPEN:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Preview is not available")
    if preview.freshness_label != "fresh":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Preview quote is not fresh")

    if preview.side == SIDE_BUY and money(preview.notional) + money(preview.fee) > money(wallet.balance):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Insufficient buying power")
    if preview.side == SIDE_SELL:
        held = held_quantity(db, portfolio.id, preview.symbol)
        if qty(preview.quantity) > held:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Insufficient holdings")

    order = SimOrder(
        portfolio_id=portfolio.id,
        wallet_id=wallet.id,
        owner_user_id=user_id,
        preview_id=preview.id,
        symbol=preview.symbol,
        side=preview.side,
        quantity=preview.quantity,
        notional=preview.notional,
        status=ORDER_STATUS_EXECUTED,
        idempotency_key=cleaned_key,
        request_fingerprint=preview.request_fingerprint,
        quote_id=preview.quote_id,
    )
    db.add(order)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        again = (
            db.query(SimOrder)
            .filter(SimOrder.owner_user_id == user_id, SimOrder.idempotency_key == cleaned_key)
            .one_or_none()
        )
        if again is not None and again.receipt is not None:
            return _receipt_out(again.receipt)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Unable to confirm order") from exc

    preview.status = PREVIEW_STATUS_CONSUMED

    execution = SimExecution(
        order_id=order.id,
        symbol=preview.symbol,
        side=preview.side,
        quantity=preview.quantity,
        price=preview.execution_price,
        notional=preview.notional,
        fee=preview.fee,
        slippage_bps=preview.slippage_bps,
        quote_id=preview.quote_id,
        quote_as_of=preview.quote_as_of,
        quote_received_at=preview.quote_received_at,
        provider=preview.provider,
        freshness_label=preview.freshness_label,
        data_mode=preview.data_mode,
        execution_policy=preview.execution_policy,
    )
    db.add(execution)
    db.flush()

    ledger_ids: list[str] = []
    prior_held = held_quantity(db, portfolio.id, preview.symbol)

    if preview.side == SIDE_BUY:
        debit = append_ledger(
            db,
            wallet=wallet,
            amount=-money(preview.notional),
            source_type=SOURCE_ORDER_DEBIT,
            idempotency_key=f"debit:{cleaned_key}",
            actor="trading_engine",
            reason=f"Simulated buy {preview.symbol}",
            audit_actor=subject.subject,
            related_order_id=order.id,
        )
        ledger_ids.append(str(debit.id))
        if money(preview.fee) > 0:
            fee_entry = append_ledger(
                db,
                wallet=wallet,
                amount=-money(preview.fee),
                source_type=SOURCE_ORDER_DEBIT,
                idempotency_key=f"fee:{cleaned_key}",
                actor="trading_engine",
                reason=f"Simulated fee {preview.symbol}",
                audit_actor=subject.subject,
                related_order_id=order.id,
            )
            ledger_ids.append(str(fee_entry.id))
        apply_buy(
            db,
            portfolio_id=portfolio.id,
            symbol=preview.symbol,
            quantity=preview.quantity,
            price=preview.execution_price,
            execution_id=execution.id,
        )
        position_delta = qty_str(preview.quantity)
    else:
        apply_sell(
            db,
            portfolio_id=portfolio.id,
            symbol=preview.symbol,
            quantity=preview.quantity,
        )
        credit = append_ledger(
            db,
            wallet=wallet,
            amount=money(preview.notional),
            source_type=SOURCE_SALE_PROCEEDS,
            idempotency_key=f"credit:{cleaned_key}",
            actor="trading_engine",
            reason=f"Simulated sell {preview.symbol}",
            audit_actor=subject.subject,
            related_order_id=order.id,
        )
        ledger_ids.append(str(credit.id))
        position_delta = qty_str(-qty(preview.quantity))

    after_held = held_quantity(db, portfolio.id, preview.symbol)
    receipt = OrderReceipt(
        order_id=order.id,
        portfolio_id=portfolio.id,
        owner_user_id=user_id,
        payload_json={},
    )
    db.add(receipt)
    db.flush()

    payload: dict[str, Any] = {
        "receipt_id": str(receipt.id),
        "order_id": str(order.id),
        "request_id": order.idempotency_key,
        "portfolio_id": str(order.portfolio_id),
        "status": order.status,
        "symbol": order.symbol,
        "side": order.side,
        "quantity": qty_str(order.quantity),
        "notional": money_str(order.notional),
        "execution_price": money_str(execution.price),
        "fee": money_str(execution.fee),
        "slippage_bps": money_str(execution.slippage_bps),
        "ledger_entry_ids": ledger_ids,
        "position_quantity": qty_str(after_held),
        "position_delta": position_delta,
        "cash_balance": money_str(wallet.balance),
        "quote": {
            "quote_id": execution.quote_id,
            "quote_as_of": execution.quote_as_of.isoformat(),
            "quote_received_at": execution.quote_received_at.isoformat(),
            "provider": execution.provider,
            "freshness_label": execution.freshness_label,
            "data_mode": execution.data_mode,
            "execution_policy": execution.execution_policy,
        },
        "simulated_at": execution.simulated_at.isoformat() if execution.simulated_at else now.isoformat(),
        "disclosure": DISCLOSURE_SIMULATED,
        "created_at": receipt.created_at.isoformat() if receipt.created_at else now.isoformat(),
    }
    receipt.payload_json = payload

    record_audit_event(
        db,
        actor_subject=subject.subject,
        action=AUDIT_ORDER_CONFIRM,
        resource_type="sim_order",
        resource_id=str(order.id),
        metadata={
            "portfolio_id": str(portfolio.id),
            "preview_id": str(preview.id),
            "symbol": order.symbol,
            "side": order.side,
            "quantity": qty_str(order.quantity),
            "notional": money_str(order.notional),
            "prior_held": qty_str(prior_held),
            "after_held": qty_str(after_held),
            "idempotency_key": cleaned_key,
        },
    )
    db.commit()
    db.refresh(receipt)
    return _receipt_out(receipt)


def get_receipt(
    db: Session,
    subject: AuthenticatedSubject,
    portfolio_id: uuid.UUID,
    order_id: uuid.UUID,
) -> OrderReceiptOut:
    get_owned_portfolio(db, subject, portfolio_id)
    order = (
        db.query(SimOrder)
        .filter(SimOrder.id == order_id, SimOrder.portfolio_id == portfolio_id)
        .one_or_none()
    )
    if order is None or order.receipt is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Receipt not found")
    return _receipt_out(order.receipt)


def list_activity(
    db: Session,
    subject: AuthenticatedSubject,
    portfolio_id: uuid.UUID,
) -> ActivityListOut:
    get_owned_portfolio(db, subject, portfolio_id)
    try:
        receipts = (
            db.query(OrderReceipt)
            .filter(OrderReceipt.portfolio_id == portfolio_id)
            .order_by(OrderReceipt.created_at.desc())
            .limit(100)
            .all()
        )
    except SQLAlchemyError:
        # Unmigrated / missing order tables must not 500 the portfolio workspace.
        db.rollback()
        return ActivityListOut(items=[])
    items: list[ActivityItemOut] = []
    for receipt in receipts:
        payload = receipt.payload_json or {}
        items.append(
            ActivityItemOut(
                receipt_id=str(receipt.id),
                order_id=str(receipt.order_id),
                symbol=str(payload.get("symbol", "")),
                side=str(payload.get("side", "")),
                status=str(payload.get("status", "")),
                quantity=str(payload.get("quantity", "0")),
                notional=str(payload.get("notional", "0")),
                created_at=receipt.created_at,
                disclosure=DISCLOSURE_SIMULATED,
            )
        )
    return ActivityListOut(items=items)


def get_positions(
    db: Session,
    subject: AuthenticatedSubject,
    portfolio_id: uuid.UUID,
) -> PositionsListOut:
    get_owned_portfolio(db, subject, portfolio_id)
    try:
        rows = list_positions(db, portfolio_id)
    except SQLAlchemyError:
        # Unmigrated / missing position tables must not 500 the portfolio workspace.
        db.rollback()
        return PositionsListOut(positions=[])
    return PositionsListOut(
        positions=[
            PositionOut(
                symbol=p.symbol,
                quantity=qty_str(p.quantity),
                avg_cost=money_str(p.avg_cost),
            )
            for p in rows
        ]
    )


def get_reconciliation(
    db: Session,
    subject: AuthenticatedSubject,
    portfolio_id: uuid.UUID,
) -> ReconciliationOut:
    portfolio = get_owned_portfolio(db, subject, portfolio_id)
    wallet = _require_wallet(portfolio)
    report = reconcile_portfolio(db, wallet=wallet, portfolio_id=portfolio.id)
    return ReconciliationOut(**report)
