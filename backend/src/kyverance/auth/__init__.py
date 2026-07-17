"""Authentication dependencies — JWT verification and development identity."""

from kyverance.auth.authorize import require_role
from kyverance.auth.deps import get_optional_subject, require_authenticated
from kyverance.auth.models import DEV_SUBJECT, AuthenticatedSubject

__all__ = [
    "AuthenticatedSubject",
    "DEV_SUBJECT",
    "get_optional_subject",
    "require_authenticated",
    "require_role",
]
