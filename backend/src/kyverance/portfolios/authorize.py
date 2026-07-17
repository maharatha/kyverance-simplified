"""Object-level portfolio and version authorization."""

from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from kyverance.auth.models import AuthenticatedSubject
from kyverance.identity.roles import RoleKey
from kyverance.portfolios.constants import (
    LICENSE_PUBLIC_FORK_ALLOWED,
    VERSION_STATUS_PUBLISHED,
    VERSION_VISIBILITY_PUBLIC,
)
from kyverance.portfolios.models import Portfolio, PortfolioVersion


def require_user_id(subject: AuthenticatedSubject) -> uuid.UUID:
    if not subject.user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    return uuid.UUID(subject.user_id)


def get_owned_portfolio(
    db: Session,
    subject: AuthenticatedSubject,
    portfolio_id: uuid.UUID,
) -> Portfolio:
    """Return the portfolio only when the subject is the owner.

    Non-owners and unknown IDs both receive a neutral 404 to avoid existence leakage.
    """
    user_id = require_user_id(subject)
    portfolio = (
        db.query(Portfolio)
        .filter(Portfolio.id == portfolio_id, Portfolio.owner_user_id == user_id)
        .one_or_none()
    )
    if portfolio is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found")
    return portfolio


def require_creator_role(subject: AuthenticatedSubject) -> None:
    """Publish requires creator (or administrator). Members may create draft versions and fork."""
    if subject.is_administrator or subject.has_role(RoleKey.CREATOR):
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")


def get_owned_version(
    db: Session,
    subject: AuthenticatedSubject,
    portfolio_id: uuid.UUID,
    version_id: uuid.UUID,
) -> PortfolioVersion:
    get_owned_portfolio(db, subject, portfolio_id)
    version = (
        db.query(PortfolioVersion)
        .filter(
            PortfolioVersion.id == version_id,
            PortfolioVersion.portfolio_id == portfolio_id,
        )
        .one_or_none()
    )
    if version is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio version not found")
    return version


def get_viewable_version(
    db: Session,
    subject: AuthenticatedSubject,
    version_id: uuid.UUID,
) -> PortfolioVersion:
    """Owner may view any version; others only published public versions."""
    user_id = require_user_id(subject)
    version = db.query(PortfolioVersion).filter(PortfolioVersion.id == version_id).one_or_none()
    if version is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio version not found")
    if version.owner_user_id == user_id:
        return version
    if (
        version.status == VERSION_STATUS_PUBLISHED
        and version.visibility == VERSION_VISIBILITY_PUBLIC
    ):
        return version
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio version not found")


def get_forkable_version(
    db: Session,
    subject: AuthenticatedSubject,
    version_id: uuid.UUID,
) -> PortfolioVersion:
    """Fork requires a published public version with public_fork_allowed license."""
    # Neutral 404 for unknown / private / draft — do not leak existence to non-owners.
    version = get_viewable_version(db, subject, version_id)
    if not (
        version.status == VERSION_STATUS_PUBLISHED
        and version.visibility == VERSION_VISIBILITY_PUBLIC
        and version.license == LICENSE_PUBLIC_FORK_ALLOWED
        and version.consent_acknowledged
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Version is not available for forking",
        )
    return version
