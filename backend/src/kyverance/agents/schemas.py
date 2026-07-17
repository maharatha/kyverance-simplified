"""Strict request/response schemas for agents, facts packets, and proposals."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from kyverance.agents.constants import DISCLOSURE_SIMULATION_SCENARIO


class AgentCreateIn(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    purpose: str = Field(min_length=1, max_length=2000)
    capabilities: list[str] = Field(default_factory=list, max_length=20)
    model_provider: str | None = Field(default=None, max_length=64)
    model_name: str | None = Field(default=None, max_length=128)
    model_version: str | None = Field(default=None, max_length=64)
    prompt_template_version: str | None = Field(default=None, max_length=64)
    budget_tokens: int | None = Field(default=None, ge=0, le=1_000_000)
    budget_usd_cents: int | None = Field(default=None, ge=0, le=1_000_000)


class AgentPatchIn(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    purpose: str | None = Field(default=None, min_length=1, max_length=2000)
    capabilities: list[str] | None = Field(default=None, max_length=20)
    status: str | None = Field(default=None, max_length=32)
    budget_tokens: int | None = Field(default=None, ge=0, le=1_000_000)
    budget_usd_cents: int | None = Field(default=None, ge=0, le=1_000_000)


class AgentOut(BaseModel):
    id: str
    portfolio_id: str
    name: str
    purpose: str
    capabilities: list[str]
    status: str
    model_provider: str
    model_name: str
    model_version: str
    prompt_template_version: str
    budget_tokens: int
    budget_usd_cents: int
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime
    can_execute_orders: bool = False
    disclosure: str = DISCLOSURE_SIMULATION_SCENARIO


class AgentListOut(BaseModel):
    agents: list[AgentOut]
    empty_state: str = "No agents yet. Create a private agent configuration for this portfolio."


class FactsPacketCreateIn(BaseModel):
    """Optional body; facts are always derived from authorized portfolio state."""

    portfolio_version_id: str | None = Field(default=None, max_length=36)


class EvidenceRefOut(BaseModel):
    kind: str
    ref: str
    label: str


class HoldingFactOut(BaseModel):
    symbol: str
    quantity: str
    avg_cost: str


class FactsPacketOut(BaseModel):
    id: str
    portfolio_id: str
    portfolio_version_id: str | None
    data_as_of: datetime
    evidence_refs: list[EvidenceRefOut]
    holdings: list[HoldingFactOut]
    cash: dict[str, Any]
    risk_inputs: dict[str, Any]
    checksum: str
    created_at: datetime
    immutable: bool = True


class ProposalGenerateIn(BaseModel):
    facts_packet_id: str | None = Field(default=None, max_length=36)
    proposal_type: str | None = Field(default=None, max_length=64)
    horizon: str | None = Field(default=None, max_length=64)


class ProposalActionOut(BaseModel):
    action: str
    symbol: str | None = None
    quantity: str | None = None
    rationale: str


class ProposalOut(BaseModel):
    id: str
    agent_id: str
    agent_name: str
    portfolio_id: str
    facts_packet_id: str
    facts_checksum: str
    proposal_type: str
    horizon: str
    assumptions: list[str]
    actions: list[ProposalActionOut]
    draft_allocation: dict[str, Any]
    evidence_refs: list[EvidenceRefOut]
    confidence: str
    limitations: str
    safety_decision: str
    model_provider: str
    model_name: str
    model_version: str
    prompt_template_version: str
    cost_usd_cents: int
    latency_ms: int
    status: str
    summary: str
    data_as_of: datetime
    created_at: datetime
    disclosure: str = DISCLOSURE_SIMULATION_SCENARIO
    scenario_label: str = "Simulation scenario"
    can_execute: bool = False
    can_auto_trade: bool = False
    review_cta: str = "Review proposal"


class ProposalListOut(BaseModel):
    proposals: list[ProposalOut]
    empty_state: str = "No proposals yet. Generate a deterministic fixture proposal to review."


class ProposalStatusPatchIn(BaseModel):
    status: str = Field(min_length=1, max_length=32)
