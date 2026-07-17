from __future__ import annotations

from dataclasses import dataclass, field

from kyverance.identity.roles import RoleKey


@dataclass(frozen=True)
class AuthenticatedSubject:
    """Normalized authenticated actor for policy checks and audit."""

    subject: str
    user_id: str | None = None
    display_name: str | None = None
    given_name: str | None = None
    family_name: str | None = None
    idp: str | None = None
    roles: frozenset[str] = field(default_factory=frozenset)
    is_dev: bool = False

    @property
    def name(self) -> str | None:
        if self.display_name:
            return self.display_name
        parts = [p for p in (self.given_name, self.family_name) if p]
        return " ".join(parts) if parts else None

    def has_role(self, role_key: str | RoleKey) -> bool:
        key = role_key.value if isinstance(role_key, RoleKey) else role_key
        return key in self.roles

    @property
    def is_administrator(self) -> bool:
        return self.has_role(RoleKey.ADMINISTRATOR)


DEV_SUBJECT = AuthenticatedSubject(
    subject="dev-user-001",
    display_name="Dev User",
    given_name="Dev",
    family_name="User",
    idp="local-development",
    roles=frozenset({RoleKey.MEMBER.value}),
    is_dev=True,
)
