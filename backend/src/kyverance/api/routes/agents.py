"""Agent registry, facts packets, and proposal API routes (AGENT-01)."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from kyverance.agents import service as agents_service
from kyverance.agents.schemas import (
    AgentCreateIn,
    AgentListOut,
    AgentOut,
    AgentPatchIn,
    FactsPacketCreateIn,
    FactsPacketOut,
    ProposalGenerateIn,
    ProposalListOut,
    ProposalOut,
    ProposalStatusPatchIn,
)
from kyverance.auth.deps import require_authenticated
from kyverance.auth.models import AuthenticatedSubject
from kyverance.db.session import get_db

router = APIRouter(prefix="/portfolios", tags=["agents"])
proposals_router = APIRouter(prefix="/agent-proposals", tags=["agents"])


@router.get("/{portfolio_id}/agents", response_model=AgentListOut)
def list_agents(
    portfolio_id: uuid.UUID,
    subject: Annotated[AuthenticatedSubject, Depends(require_authenticated)],
    db: Annotated[Session, Depends(get_db)],
) -> AgentListOut:
    return agents_service.list_agents(db, subject, portfolio_id)


@router.post("/{portfolio_id}/agents", response_model=AgentOut, status_code=201)
def create_agent(
    portfolio_id: uuid.UUID,
    body: AgentCreateIn,
    subject: Annotated[AuthenticatedSubject, Depends(require_authenticated)],
    db: Annotated[Session, Depends(get_db)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> AgentOut:
    return agents_service.create_agent(
        db,
        subject,
        portfolio_id,
        name=body.name,
        purpose=body.purpose,
        capabilities=body.capabilities,
        model_provider=body.model_provider,
        model_name=body.model_name,
        model_version=body.model_version,
        prompt_template_version=body.prompt_template_version,
        budget_tokens=body.budget_tokens,
        budget_usd_cents=body.budget_usd_cents,
        idempotency_key=idempotency_key,
    )


@router.get("/{portfolio_id}/agents/{agent_id}", response_model=AgentOut)
def get_agent(
    portfolio_id: uuid.UUID,
    agent_id: uuid.UUID,
    subject: Annotated[AuthenticatedSubject, Depends(require_authenticated)],
    db: Annotated[Session, Depends(get_db)],
) -> AgentOut:
    return agents_service.get_agent(db, subject, portfolio_id, agent_id)


@router.patch("/{portfolio_id}/agents/{agent_id}", response_model=AgentOut)
def patch_agent(
    portfolio_id: uuid.UUID,
    agent_id: uuid.UUID,
    body: AgentPatchIn,
    subject: Annotated[AuthenticatedSubject, Depends(require_authenticated)],
    db: Annotated[Session, Depends(get_db)],
) -> AgentOut:
    return agents_service.patch_agent(
        db,
        subject,
        portfolio_id,
        agent_id,
        name=body.name,
        purpose=body.purpose,
        capabilities=body.capabilities,
        status_value=body.status,
        budget_tokens=body.budget_tokens,
        budget_usd_cents=body.budget_usd_cents,
    )


@router.post(
    "/{portfolio_id}/facts-packets",
    response_model=FactsPacketOut,
    status_code=201,
)
def create_facts_packet(
    portfolio_id: uuid.UUID,
    subject: Annotated[AuthenticatedSubject, Depends(require_authenticated)],
    db: Annotated[Session, Depends(get_db)],
    body: FactsPacketCreateIn | None = None,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> FactsPacketOut:
    version_id = None
    if body and body.portfolio_version_id:
        version_id = uuid.UUID(body.portfolio_version_id)
    return agents_service.create_facts_packet(
        db,
        subject,
        portfolio_id,
        portfolio_version_id=version_id,
        idempotency_key=idempotency_key,
    )


@router.get(
    "/{portfolio_id}/facts-packets/{facts_packet_id}",
    response_model=FactsPacketOut,
)
def get_facts_packet(
    portfolio_id: uuid.UUID,
    facts_packet_id: uuid.UUID,
    subject: Annotated[AuthenticatedSubject, Depends(require_authenticated)],
    db: Annotated[Session, Depends(get_db)],
) -> FactsPacketOut:
    return agents_service.get_facts_packet(db, subject, portfolio_id, facts_packet_id)


@router.get("/{portfolio_id}/proposals", response_model=ProposalListOut)
def list_proposals(
    portfolio_id: uuid.UUID,
    subject: Annotated[AuthenticatedSubject, Depends(require_authenticated)],
    db: Annotated[Session, Depends(get_db)],
) -> ProposalListOut:
    return agents_service.list_proposals(db, subject, portfolio_id)


@router.post(
    "/{portfolio_id}/agents/{agent_id}/proposals",
    response_model=ProposalOut,
    status_code=201,
)
def generate_proposal(
    portfolio_id: uuid.UUID,
    agent_id: uuid.UUID,
    subject: Annotated[AuthenticatedSubject, Depends(require_authenticated)],
    db: Annotated[Session, Depends(get_db)],
    body: ProposalGenerateIn | None = None,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> ProposalOut:
    facts_id = None
    proposal_type = None
    horizon = None
    if body:
        if body.facts_packet_id:
            facts_id = uuid.UUID(body.facts_packet_id)
        proposal_type = body.proposal_type
        horizon = body.horizon
    return agents_service.generate_proposal(
        db,
        subject,
        portfolio_id,
        agent_id,
        facts_packet_id=facts_id,
        proposal_type=proposal_type,
        horizon=horizon,
        idempotency_key=idempotency_key,
    )


@router.get("/{portfolio_id}/proposals/{proposal_id}", response_model=ProposalOut)
def get_proposal(
    portfolio_id: uuid.UUID,
    proposal_id: uuid.UUID,
    subject: Annotated[AuthenticatedSubject, Depends(require_authenticated)],
    db: Annotated[Session, Depends(get_db)],
) -> ProposalOut:
    return agents_service.get_proposal(db, subject, portfolio_id, proposal_id)


@router.patch("/{portfolio_id}/proposals/{proposal_id}", response_model=ProposalOut)
def patch_proposal_status(
    portfolio_id: uuid.UUID,
    proposal_id: uuid.UUID,
    body: ProposalStatusPatchIn,
    subject: Annotated[AuthenticatedSubject, Depends(require_authenticated)],
    db: Annotated[Session, Depends(get_db)],
) -> ProposalOut:
    return agents_service.patch_proposal_status(
        db,
        subject,
        portfolio_id,
        proposal_id,
        status_value=body.status,
    )


@proposals_router.get("/{proposal_id}", response_model=ProposalOut)
def get_proposal_global(
    proposal_id: uuid.UUID,
    subject: Annotated[AuthenticatedSubject, Depends(require_authenticated)],
    db: Annotated[Session, Depends(get_db)],
) -> ProposalOut:
    return agents_service.get_proposal_global(db, subject, proposal_id)
