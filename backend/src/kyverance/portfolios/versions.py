"""Immutable portfolio versions, publish consent, and independent forks."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from kyverance.audit.service import record_audit_event
from kyverance.auth.models import AuthenticatedSubject
from kyverance.config import get_settings
from kyverance.portfolios import service as portfolios_service
from kyverance.portfolios.authorize import (
    get_forkable_version,
    get_owned_portfolio,
    get_owned_version,
    get_viewable_version,
    require_creator_role,
    require_user_id,
)
from kyverance.portfolios.constants import (
    ALLOWED_PROVENANCE,
    ALLOWED_PUBLISH_LICENSES,
    ALLOWED_PUBLISH_VISIBILITIES,
    AUDIT_PORTFOLIO_FORK,
    AUDIT_VERSION_CREATE,
    AUDIT_VERSION_PUBLISH,
    CONSENT_TEXT_VERSION,
    DISCLOSURE_SIMULATED_PUBLISH,
    FORK_ENTITLEMENT_PUBLIC_VERSION,
    FORK_NOTICE,
    LICENSE_PUBLIC_FORK_ALLOWED,
    SOURCE_FORK_SEED_ALLOCATION,
    VERSION_STATUS_DRAFT,
    VERSION_STATUS_PUBLISHED,
    VERSION_VISIBILITY_PRIVATE,
    VERSION_VISIBILITY_PUBLIC,
)
from kyverance.portfolios.models import Portfolio, PortfolioFork, PortfolioVersion
from kyverance.portfolios.schemas import (
    ForkCreateIn,
    HoldingSnapshotOut,
    PortfolioVersionListOut,
    PortfolioVersionOut,
    PortfolioVersionPublishIn,
)
from kyverance.simulation.constants import (
    FUNDING_BUCKET_COMPLIMENTARY,
    PORTFOLIO_PROVENANCE_SIMULATED,
    PORTFOLIO_STATUS_ACTIVE,
    PORTFOLIO_VISIBILITY_PRIVATE,
    VIRTUAL_CURRENCY_CODE,
)
from kyverance.simulation.models import SimPosition, SimPositionLot, SimWallet
from kyverance.simulation.money import money, money_str, qty, qty_str
from kyverance.simulation.positions import list_positions


def _canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _checksum(payload: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _holdings_snapshot(db: Session, portfolio_id: uuid.UUID) -> list[dict[str, str]]:
    rows = list_positions(db, portfolio_id)
    return [
        {
            "symbol": pos.symbol,
            "quantity": qty_str(pos.quantity),
            "avg_cost": money_str(pos.avg_cost),
        }
        for pos in rows
        if qty(pos.quantity) > 0
    ]


def _allocation_snapshot(wallet: SimWallet, holdings: list[dict[str, str]]) -> dict[str, Any]:
    return {
        "cash_balance": money_str(wallet.balance),
        "complimentary_balance": money_str(wallet.complimentary_balance),
        "currency_code": wallet.currency_code,
        "holdings_count": len(holdings),
    }


def _data_context_snapshot() -> dict[str, Any]:
    settings = get_settings()
    return {
        "currency_code": VIRTUAL_CURRENCY_CODE,
        "quote_mode": getattr(settings, "quote_mode", "fixture"),
        "simulation_only": True,
        "plaid_excluded": True,
        "captured_at": datetime.now(UTC).isoformat(),
    }


def _version_out(version: PortfolioVersion) -> PortfolioVersionOut:
    fork_allowed = (
        version.status == VERSION_STATUS_PUBLISHED
        and version.visibility == VERSION_VISIBILITY_PUBLIC
        and version.license == LICENSE_PUBLIC_FORK_ALLOWED
        and version.consent_acknowledged
    )
    holdings = [
        HoldingSnapshotOut(
            symbol=str(item.get("symbol", "")),
            quantity=str(item.get("quantity", "0")),
            avg_cost=str(item.get("avg_cost", "0")),
        )
        for item in (version.holdings_json or [])
        if isinstance(item, dict)
    ]
    return PortfolioVersionOut(
        id=str(version.id),
        portfolio_id=str(version.portfolio_id),
        version_number=int(version.version_number),
        name=version.name,
        description=version.description,
        thesis=version.thesis,
        agent_config_ref=version.agent_config_ref,
        holdings=holdings,
        allocation=dict(version.allocation_json or {}),
        data_context=dict(version.data_context_json or {}),
        checksum=version.checksum,
        status=version.status,
        visibility=version.visibility,
        provenance=version.provenance,
        license=version.license,
        disclosure=version.disclosure,
        consent_acknowledged=bool(version.consent_acknowledged),
        consent_text_version=version.consent_text_version,
        consent_at=version.consent_at,
        published_at=version.published_at,
        created_at=version.created_at,
        fork_allowed=fork_allowed,
        fork_notice=FORK_NOTICE if fork_allowed else None,
    )


def create_version(
    db: Session,
    subject: AuthenticatedSubject,
    portfolio_id: uuid.UUID,
    *,
    idempotency_key: str | None = None,
) -> PortfolioVersionOut:
    portfolio = get_owned_portfolio(db, subject, portfolio_id)
    if portfolio.wallet is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Portfolio wallet is missing",
        )
    cleaned_key = idempotency_key.strip() if idempotency_key and idempotency_key.strip() else None
    if cleaned_key:
        existing = (
            db.query(PortfolioVersion)
            .filter(
                PortfolioVersion.portfolio_id == portfolio.id,
                PortfolioVersion.creation_idempotency_key == cleaned_key,
            )
            .one_or_none()
        )
        if existing is not None:
            return _version_out(existing)

    holdings = _holdings_snapshot(db, portfolio.id)
    allocation = _allocation_snapshot(portfolio.wallet, holdings)
    data_context = _data_context_snapshot()
    checksum_payload = {
        "portfolio_id": str(portfolio.id),
        "name": portfolio.name,
        "description": portfolio.description,
        "thesis": portfolio.thesis,
        "agent_config_ref": portfolio.agent_config_ref,
        "holdings": holdings,
        "allocation": allocation,
        "data_context": {
            "currency_code": data_context["currency_code"],
            "quote_mode": data_context["quote_mode"],
            "simulation_only": True,
            "plaid_excluded": True,
        },
        "provenance": portfolio.provenance,
    }
    next_number = (
        db.query(func.coalesce(func.max(PortfolioVersion.version_number), 0))
        .filter(PortfolioVersion.portfolio_id == portfolio.id)
        .scalar()
    )
    version = PortfolioVersion(
        portfolio_id=portfolio.id,
        owner_user_id=portfolio.owner_user_id,
        version_number=int(next_number) + 1,
        name=portfolio.name,
        description=portfolio.description,
        thesis=portfolio.thesis,
        agent_config_ref=portfolio.agent_config_ref,
        holdings_json=holdings,
        allocation_json=allocation,
        data_context_json=data_context,
        checksum=_checksum(checksum_payload),
        status=VERSION_STATUS_DRAFT,
        visibility=VERSION_VISIBILITY_PRIVATE,
        provenance=PORTFOLIO_PROVENANCE_SIMULATED,
        creation_idempotency_key=cleaned_key,
    )
    db.add(version)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        if cleaned_key:
            existing = (
                db.query(PortfolioVersion)
                .filter(
                    PortfolioVersion.portfolio_id == portfolio_id,
                    PortfolioVersion.creation_idempotency_key == cleaned_key,
                )
                .one_or_none()
            )
            if existing is not None:
                return _version_out(existing)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Unable to create portfolio version",
        ) from exc

    record_audit_event(
        db,
        actor_subject=subject.subject,
        action=AUDIT_VERSION_CREATE,
        resource_type="portfolio_version",
        resource_id=str(version.id),
        metadata={
            "portfolio_id": str(portfolio.id),
            "version_number": version.version_number,
            "checksum": version.checksum,
            "idempotency_key": cleaned_key,
        },
    )
    db.commit()
    db.refresh(version)
    return _version_out(version)


def list_versions(
    db: Session,
    subject: AuthenticatedSubject,
    portfolio_id: uuid.UUID,
) -> PortfolioVersionListOut:
    get_owned_portfolio(db, subject, portfolio_id)
    versions = (
        db.query(PortfolioVersion)
        .filter(PortfolioVersion.portfolio_id == portfolio_id)
        .order_by(PortfolioVersion.version_number.desc())
        .all()
    )
    return PortfolioVersionListOut(versions=[_version_out(v) for v in versions])


def get_version(
    db: Session,
    subject: AuthenticatedSubject,
    version_id: uuid.UUID,
) -> PortfolioVersionOut:
    version = get_viewable_version(db, subject, version_id)
    return _version_out(version)


def get_owned_portfolio_version(
    db: Session,
    subject: AuthenticatedSubject,
    portfolio_id: uuid.UUID,
    version_id: uuid.UUID,
) -> PortfolioVersionOut:
    version = get_owned_version(db, subject, portfolio_id, version_id)
    return _version_out(version)


def publish_version(
    db: Session,
    subject: AuthenticatedSubject,
    portfolio_id: uuid.UUID,
    version_id: uuid.UUID,
    body: PortfolioVersionPublishIn,
) -> PortfolioVersionOut:
    require_creator_role(subject)
    version = get_owned_version(db, subject, portfolio_id, version_id)

    visibility = (body.visibility or "").strip().lower()
    license_key = (body.license or "").strip().lower()
    provenance = (body.provenance or "").strip().lower()

    if visibility not in ALLOWED_PUBLISH_VISIBILITIES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid visibility")
    if license_key not in ALLOWED_PUBLISH_LICENSES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid license")
    if provenance not in ALLOWED_PROVENANCE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only simulated provenance is allowed for FORK-01 publishing",
        )
    if not body.consent_acknowledged:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Explicit publish consent is required",
        )
    if not body.disclosure_acknowledged:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Disclosure acknowledgement is required",
        )
    if visibility == VERSION_VISIBILITY_PUBLIC and license_key == LICENSE_PUBLIC_FORK_ALLOWED:
        # Public fork-capable publish is allowed.
        pass
    if version.status == VERSION_STATUS_PUBLISHED:
        # Idempotent re-publish with same policy returns current row; changing policy is blocked.
        if (
            version.visibility == visibility
            and version.license == license_key
            and version.provenance == provenance
            and version.consent_acknowledged
        ):
            return _version_out(version)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Published versions are immutable; create a new version to change publish policy",
        )

    now = datetime.now(UTC)
    version.status = VERSION_STATUS_PUBLISHED
    version.visibility = visibility
    version.license = license_key
    version.provenance = provenance
    version.disclosure = DISCLOSURE_SIMULATED_PUBLISH
    version.consent_acknowledged = True
    version.consent_text_version = CONSENT_TEXT_VERSION
    version.consent_at = now
    version.published_at = now
    version.published_by_user_id = require_user_id(subject)
    db.flush()

    # Snapshot content itself remains immutable; only publish metadata is set once.
    record_audit_event(
        db,
        actor_subject=subject.subject,
        action=AUDIT_VERSION_PUBLISH,
        resource_type="portfolio_version",
        resource_id=str(version.id),
        metadata={
            "portfolio_id": str(portfolio_id),
            "visibility": visibility,
            "license": license_key,
            "provenance": provenance,
            "consent_text_version": CONSENT_TEXT_VERSION,
            "checksum": version.checksum,
        },
    )
    db.commit()
    db.refresh(version)
    return _version_out(version)


def _seed_fork_positions(
    db: Session,
    *,
    portfolio_id: uuid.UUID,
    holdings: list[dict[str, Any]],
) -> None:
    for item in holdings:
        symbol = str(item.get("symbol", "")).strip().upper()
        if not symbol:
            continue
        quantity = qty(item.get("quantity", "0"))
        avg_cost = money(item.get("avg_cost", "0"))
        if quantity <= 0:
            continue
        db.add(
            SimPosition(
                portfolio_id=portfolio_id,
                symbol=symbol,
                quantity=quantity,
                avg_cost=avg_cost,
            )
        )
        db.add(
            SimPositionLot(
                portfolio_id=portfolio_id,
                symbol=symbol,
                quantity_remaining=quantity,
                unit_cost=avg_cost,
                execution_id=None,
            )
        )
    db.flush()


def fork_version(
    db: Session,
    subject: AuthenticatedSubject,
    version_id: uuid.UUID,
    body: ForkCreateIn | None = None,
    *,
    idempotency_key: str | None = None,
):
    """Create an independent simulated portfolio from exactly one permitted public version."""
    user_id = require_user_id(subject)
    version = get_forkable_version(db, subject, version_id)
    cleaned_key = idempotency_key.strip() if idempotency_key and idempotency_key.strip() else None
    if cleaned_key:
        existing_fork = (
            db.query(PortfolioFork)
            .filter(
                PortfolioFork.forked_by_user_id == user_id,
                PortfolioFork.creation_idempotency_key == cleaned_key,
            )
            .one_or_none()
        )
        if existing_fork is not None:
            return portfolios_service.get_portfolio(db, subject, existing_fork.forked_portfolio_id)

    requested_name = body.name.strip() if body and body.name and body.name.strip() else None
    fork_name = requested_name or f"Fork of {version.name}"[:128]
    cash = money((version.allocation_json or {}).get("cash_balance", "0"))

    portfolio = Portfolio(
        owner_user_id=user_id,
        name=fork_name,
        description=version.description,
        thesis=version.thesis,
        agent_config_ref=version.agent_config_ref,
        visibility=PORTFOLIO_VISIBILITY_PRIVATE,
        provenance=PORTFOLIO_PROVENANCE_SIMULATED,
        status=PORTFOLIO_STATUS_ACTIVE,
        currency_code=VIRTUAL_CURRENCY_CODE,
        creation_idempotency_key=None,
    )
    db.add(portfolio)
    db.flush()

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

    portfolios_service.append_ledger(
        db,
        wallet=wallet,
        amount=cash,
        source_type=SOURCE_FORK_SEED_ALLOCATION,
        idempotency_key=f"fork-seed:{portfolio.id}",
        actor="system",
        reason="Independent fork seed from published version allocation (virtual cash)",
        funding_bucket=FUNDING_BUCKET_COMPLIMENTARY,
        audit_actor=subject.subject,
    )
    _seed_fork_positions(db, portfolio_id=portfolio.id, holdings=list(version.holdings_json or []))

    lineage = PortfolioFork(
        forked_portfolio_id=portfolio.id,
        source_portfolio_id=version.portfolio_id,
        source_version_id=version.id,
        forked_by_user_id=user_id,
        license=version.license or LICENSE_PUBLIC_FORK_ALLOWED,
        entitlement=FORK_ENTITLEMENT_PUBLIC_VERSION,
        sync_enabled=False,
        mirror_trades=False,
        creation_idempotency_key=cleaned_key,
    )
    db.add(lineage)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        if cleaned_key:
            existing_fork = (
                db.query(PortfolioFork)
                .filter(
                    PortfolioFork.forked_by_user_id == user_id,
                    PortfolioFork.creation_idempotency_key == cleaned_key,
                )
                .one_or_none()
            )
            if existing_fork is not None:
                return portfolios_service.get_portfolio(db, subject, existing_fork.forked_portfolio_id)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Unable to fork portfolio version",
        ) from exc

    record_audit_event(
        db,
        actor_subject=subject.subject,
        action=AUDIT_PORTFOLIO_FORK,
        resource_type="portfolio",
        resource_id=str(portfolio.id),
        metadata={
            "source_portfolio_id": str(version.portfolio_id),
            "source_version_id": str(version.id),
            "license": lineage.license,
            "entitlement": lineage.entitlement,
            "sync_enabled": False,
            "mirror_trades": False,
            "checksum": version.checksum,
            "idempotency_key": cleaned_key,
        },
    )
    db.commit()
    db.refresh(portfolio)
    return portfolios_service.get_portfolio(db, subject, portfolio.id)
