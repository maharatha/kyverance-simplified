from __future__ import annotations

from enum import StrEnum


class RoleKey(StrEnum):
    MEMBER = "member"
    CREATOR = "creator"
    MODERATOR = "moderator"
    SUPPORT = "support"
    FINANCE_OPERATIONS = "finance_operations"
    ADMINISTRATOR = "administrator"
    AGENT_SERVICE = "agent_service"


ROLE_DISPLAY_NAMES: dict[RoleKey, str] = {
    RoleKey.MEMBER: "Member",
    RoleKey.CREATOR: "Creator",
    RoleKey.MODERATOR: "Moderator",
    RoleKey.SUPPORT: "Support",
    RoleKey.FINANCE_OPERATIONS: "Finance Operations",
    RoleKey.ADMINISTRATOR: "Administrator",
    RoleKey.AGENT_SERVICE: "Agent Service",
}

ALL_ROLE_KEYS: frozenset[str] = frozenset(role.value for role in RoleKey)
DEFAULT_ROLE_KEY = RoleKey.MEMBER.value
