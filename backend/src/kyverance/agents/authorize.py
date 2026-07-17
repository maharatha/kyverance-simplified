"""Object-level authorization for agents, facts packets, and proposals."""

from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from kyverance.agents.models import Agent, AgentFactsPacket, AgentProposal
from kyverance.auth.models import AuthenticatedSubject
from kyverance.portfolios.authorize import get_owned_portfolio, require_user_id


def get_owned_agent(
    db: Session,
    subject: AuthenticatedSubject,
    portfolio_id: uuid.UUID,
    agent_id: uuid.UUID,
) -> Agent:
    get_owned_portfolio(db, subject, portfolio_id)
    user_id = require_user_id(subject)
    agent = (
        db.query(Agent)
        .filter(
            Agent.id == agent_id,
            Agent.portfolio_id == portfolio_id,
            Agent.owner_user_id == user_id,
        )
        .one_or_none()
    )
    if agent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    return agent


def get_owned_facts_packet(
    db: Session,
    subject: AuthenticatedSubject,
    portfolio_id: uuid.UUID,
    facts_packet_id: uuid.UUID,
) -> AgentFactsPacket:
    get_owned_portfolio(db, subject, portfolio_id)
    user_id = require_user_id(subject)
    packet = (
        db.query(AgentFactsPacket)
        .filter(
            AgentFactsPacket.id == facts_packet_id,
            AgentFactsPacket.portfolio_id == portfolio_id,
            AgentFactsPacket.owner_user_id == user_id,
        )
        .one_or_none()
    )
    if packet is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Facts packet not found")
    return packet


def get_owned_proposal(
    db: Session,
    subject: AuthenticatedSubject,
    portfolio_id: uuid.UUID,
    proposal_id: uuid.UUID,
) -> AgentProposal:
    get_owned_portfolio(db, subject, portfolio_id)
    user_id = require_user_id(subject)
    proposal = (
        db.query(AgentProposal)
        .filter(
            AgentProposal.id == proposal_id,
            AgentProposal.portfolio_id == portfolio_id,
            AgentProposal.owner_user_id == user_id,
        )
        .one_or_none()
    )
    if proposal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proposal not found")
    return proposal


def get_owned_proposal_by_id(
    db: Session,
    subject: AuthenticatedSubject,
    proposal_id: uuid.UUID,
) -> AgentProposal:
    """Lookup by proposal id only; still enforces owner scope with neutral 404."""
    user_id = require_user_id(subject)
    proposal = (
        db.query(AgentProposal)
        .filter(AgentProposal.id == proposal_id, AgentProposal.owner_user_id == user_id)
        .one_or_none()
    )
    if proposal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proposal not found")
    return proposal
