"""Object-level portfolio authorization — owner only in SIM-01."""

from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from kyverance.auth.models import AuthenticatedSubject
from kyverance.portfolios.models import Portfolio


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
