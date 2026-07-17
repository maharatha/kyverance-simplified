"""Agent registry, facts packets, and proposal constants (AGENT-01)."""

from __future__ import annotations

AGENT_STATUS_ACTIVE = "active"
AGENT_STATUS_PAUSED = "paused"
AGENT_STATUS_ARCHIVED = "archived"

ALLOWED_AGENT_STATUSES = frozenset(
    {AGENT_STATUS_ACTIVE, AGENT_STATUS_PAUSED, AGENT_STATUS_ARCHIVED}
)

PROPOSAL_TYPE_REBALANCE = "rebalance_scenario"
PROPOSAL_TYPE_HOLD = "hold_scenario"
PROPOSAL_TYPE_RESEARCH = "research_brief"

ALLOWED_PROPOSAL_TYPES = frozenset(
    {PROPOSAL_TYPE_REBALANCE, PROPOSAL_TYPE_HOLD, PROPOSAL_TYPE_RESEARCH}
)

PROPOSAL_STATUS_READY_FOR_REVIEW = "ready_for_review"
PROPOSAL_STATUS_DISMISSED = "dismissed"

ALLOWED_PROPOSAL_STATUSES = frozenset(
    {PROPOSAL_STATUS_READY_FOR_REVIEW, PROPOSAL_STATUS_DISMISSED}
)

SAFETY_DECISION_ALLOWED = "allowed_for_review"
SAFETY_DECISION_BLOCKED = "blocked"

FIXTURE_MODEL_PROVIDER = "fixture"
FIXTURE_MODEL_NAME = "deterministic-v1"
FIXTURE_MODEL_VERSION = "1.0.0"
FIXTURE_PROMPT_TEMPLATE_VERSION = "agent-01-v1"

DEFAULT_BUDGET_TOKENS = 8_000
DEFAULT_BUDGET_USD_CENTS = 0

DISCLOSURE_SIMULATION_SCENARIO = (
    "This is a simulation scenario / draft proposal. It is not investment advice, "
    "not a trade instruction, and cannot confirm, submit, schedule, or execute orders."
)

AUDIT_AGENT_CREATE = "agent.create"
AUDIT_AGENT_UPDATE = "agent.update"
AUDIT_FACTS_CREATE = "agent.facts.create"
AUDIT_PROPOSAL_CREATE = "agent.proposal.create"
AUDIT_PROPOSAL_STATUS = "agent.proposal.status_change"
