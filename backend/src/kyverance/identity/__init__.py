"""Identity module — Entra subject mapping, profile, roles, consents."""

from kyverance.identity.models import ConsentRecord, RoleGrant, User
from kyverance.identity.roles import ALL_ROLE_KEYS, DEFAULT_ROLE_KEY, ROLE_DISPLAY_NAMES, RoleKey
from kyverance.identity.service import bootstrap_user_on_sign_in, grant_role, record_consent

__all__ = [
    "ALL_ROLE_KEYS",
    "DEFAULT_ROLE_KEY",
    "ROLE_DISPLAY_NAMES",
    "ConsentRecord",
    "RoleGrant",
    "RoleKey",
    "User",
    "bootstrap_user_on_sign_in",
    "grant_role",
    "record_consent",
]
