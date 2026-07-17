from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException, status

from kyverance.auth.deps import require_authenticated
from kyverance.auth.models import AuthenticatedSubject
from kyverance.identity.roles import RoleKey


def require_role(*role_keys: str | RoleKey) -> Callable[..., AuthenticatedSubject]:
    """Deny-by-default role gate. Missing required role → neutral 403."""
    required = frozenset(key.value if isinstance(key, RoleKey) else key for key in role_keys)

    def dependency(
        subject: Annotated[AuthenticatedSubject, Depends(require_authenticated)],
    ) -> AuthenticatedSubject:
        if subject.is_administrator:
            return subject
        if required and not (subject.roles & required):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient role",
            )
        return subject

    return dependency
