"""Agent registry, facts packets, and deterministic fixture proposals (AGENT-01)."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from kyverance.agents.authorize import (
    get_owned_agent,
    get_owned_facts_packet,
    get_owned_proposal,
    get_owned_proposal_by_id,
)
from kyverance.agents.constants import (
    AGENT_STATUS_ACTIVE,
    ALLOWED_AGENT_STATUSES,
    ALLOWED_PROPOSAL_STATUSES,
    ALLOWED_PROPOSAL_TYPES,
    AUDIT_AGENT_CREATE,
    AUDIT_AGENT_UPDATE,
    AUDIT_FACTS_CREATE,
    AUDIT_PROPOSAL_CREATE,
    AUDIT_PROPOSAL_STATUS,
    DEFAULT_BUDGET_TOKENS,
    DEFAULT_BUDGET_USD_CENTS,
    DISCLOSURE_SIMULATION_SCENARIO,
    FIXTURE_MODEL_NAME,
    FIXTURE_MODEL_PROVIDER,
    FIXTURE_MODEL_VERSION,
    FIXTURE_PROMPT_TEMPLATE_VERSION,
    PROPOSAL_STATUS_READY_FOR_REVIEW,
    PROPOSAL_TYPE_HOLD,
    PROPOSAL_TYPE_REBALANCE,
    SAFETY_DECISION_ALLOWED,
)
from kyverance.agents.models import Agent, AgentFactsPacket, AgentProposal
from kyverance.agents.schemas import (
    AgentListOut,
    AgentOut,
    EvidenceRefOut,
    FactsPacketOut,
    HoldingFactOut,
    ProposalActionOut,
    ProposalListOut,
    ProposalOut,
)
from kyverance.audit.service import record_audit_event
from kyverance.auth.models import AuthenticatedSubject
from kyverance.config import get_settings
from kyverance.portfolios.authorize import get_owned_portfolio, require_user_id
from kyverance.portfolios.models import PortfolioVersion
from kyverance.simulation.money import money_str, qty, qty_str
from kyverance.simulation.positions import list_positions


def _canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _checksum(payload: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _clean_str(value: str | None, *, field: str, max_len: int) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    if len(cleaned) > max_len:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field} exceeds maximum length",
        )
    return cleaned


def _clean_capabilities(raw: list[str] | None) -> list[str]:
    if not raw:
        return []
    cleaned: list[str] = []
    for item in raw[:20]:
        text = item.strip() if isinstance(item, str) else ""
        if text and text not in cleaned and len(text) <= 64:
            cleaned.append(text)
    return cleaned


def _agent_out(agent: Agent) -> AgentOut:
    return AgentOut(
        id=str(agent.id),
        portfolio_id=str(agent.portfolio_id),
        name=agent.name,
        purpose=agent.purpose,
        capabilities=list(agent.capabilities_json or []),
        status=agent.status,
        model_provider=agent.model_provider,
        model_name=agent.model_name,
        model_version=agent.model_version,
        prompt_template_version=agent.prompt_template_version,
        budget_tokens=int(agent.budget_tokens),
        budget_usd_cents=int(agent.budget_usd_cents),
        metadata=dict(agent.metadata_json or {}),
        created_at=agent.created_at,
        updated_at=agent.updated_at,
        can_execute_orders=False,
        disclosure=DISCLOSURE_SIMULATION_SCENARIO,
    )


def _evidence_outs(raw: list[Any]) -> list[EvidenceRefOut]:
    out: list[EvidenceRefOut] = []
    for item in raw or []:
        if not isinstance(item, dict):
            continue
        out.append(
            EvidenceRefOut(
                kind=str(item.get("kind", "unknown")),
                ref=str(item.get("ref", "")),
                label=str(item.get("label", "")),
            )
        )
    return out


def _facts_out(packet: AgentFactsPacket) -> FactsPacketOut:
    holdings = [
        HoldingFactOut(
            symbol=str(item.get("symbol", "")),
            quantity=str(item.get("quantity", "0")),
            avg_cost=str(item.get("avg_cost", "0")),
        )
        for item in (packet.holdings_json or [])
        if isinstance(item, dict)
    ]
    return FactsPacketOut(
        id=str(packet.id),
        portfolio_id=str(packet.portfolio_id),
        portfolio_version_id=str(packet.portfolio_version_id) if packet.portfolio_version_id else None,
        data_as_of=packet.data_as_of,
        evidence_refs=_evidence_outs(packet.evidence_refs_json or []),
        holdings=holdings,
        cash=dict(packet.cash_json or {}),
        risk_inputs=dict(packet.risk_inputs_json or {}),
        checksum=packet.checksum,
        created_at=packet.created_at,
        immutable=True,
    )


def _proposal_out(proposal: AgentProposal, *, agent_name: str) -> ProposalOut:
    actions = [
        ProposalActionOut(
            action=str(item.get("action", "")),
            symbol=item.get("symbol"),
            quantity=item.get("quantity"),
            rationale=str(item.get("rationale", "")),
        )
        for item in (proposal.actions_json or [])
        if isinstance(item, dict)
    ]
    return ProposalOut(
        id=str(proposal.id),
        agent_id=str(proposal.agent_id),
        agent_name=agent_name,
        portfolio_id=str(proposal.portfolio_id),
        facts_packet_id=str(proposal.facts_packet_id),
        facts_checksum=proposal.facts_checksum,
        proposal_type=proposal.proposal_type,
        horizon=proposal.horizon,
        assumptions=list(proposal.assumptions_json or []),
        actions=actions,
        draft_allocation=dict(proposal.draft_allocation_json or {}),
        evidence_refs=_evidence_outs(proposal.evidence_refs_json or []),
        confidence=proposal.confidence,
        limitations=proposal.limitations,
        safety_decision=proposal.safety_decision,
        model_provider=proposal.model_provider,
        model_name=proposal.model_name,
        model_version=proposal.model_version,
        prompt_template_version=proposal.prompt_template_version,
        cost_usd_cents=int(proposal.cost_usd_cents),
        latency_ms=int(proposal.latency_ms),
        status=proposal.status,
        summary=proposal.summary,
        data_as_of=proposal.data_as_of,
        created_at=proposal.created_at,
        disclosure=DISCLOSURE_SIMULATION_SCENARIO,
        scenario_label="Simulation scenario",
        can_execute=False,
        can_auto_trade=False,
        review_cta="Review proposal",
    )


def list_agents(
    db: Session,
    subject: AuthenticatedSubject,
    portfolio_id: uuid.UUID,
) -> AgentListOut:
    get_owned_portfolio(db, subject, portfolio_id)
    user_id = require_user_id(subject)
    rows = (
        db.query(Agent)
        .filter(Agent.portfolio_id == portfolio_id, Agent.owner_user_id == user_id)
        .order_by(Agent.created_at.desc())
        .all()
    )
    return AgentListOut(agents=[_agent_out(row) for row in rows])


def create_agent(
    db: Session,
    subject: AuthenticatedSubject,
    portfolio_id: uuid.UUID,
    *,
    name: str,
    purpose: str,
    capabilities: list[str] | None = None,
    model_provider: str | None = None,
    model_name: str | None = None,
    model_version: str | None = None,
    prompt_template_version: str | None = None,
    budget_tokens: int | None = None,
    budget_usd_cents: int | None = None,
    idempotency_key: str | None = None,
) -> AgentOut:
    portfolio = get_owned_portfolio(db, subject, portfolio_id)
    user_id = require_user_id(subject)
    cleaned_name = _clean_str(name, field="name", max_len=128)
    cleaned_purpose = _clean_str(purpose, field="purpose", max_len=2000)
    if not cleaned_name or not cleaned_purpose:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Name and purpose are required")
    cleaned_key = _clean_str(idempotency_key, field="Idempotency-Key", max_len=128)

    if cleaned_key:
        existing = (
            db.query(Agent)
            .filter(
                Agent.portfolio_id == portfolio_id,
                Agent.creation_idempotency_key == cleaned_key,
            )
            .one_or_none()
        )
        if existing is not None:
            return _agent_out(existing)

    agent = Agent(
        portfolio_id=portfolio.id,
        owner_user_id=user_id,
        name=cleaned_name,
        purpose=cleaned_purpose,
        capabilities_json=_clean_capabilities(capabilities),
        status=AGENT_STATUS_ACTIVE,
        model_provider=_clean_str(model_provider, field="model_provider", max_len=64)
        or FIXTURE_MODEL_PROVIDER,
        model_name=_clean_str(model_name, field="model_name", max_len=128) or FIXTURE_MODEL_NAME,
        model_version=_clean_str(model_version, field="model_version", max_len=64)
        or FIXTURE_MODEL_VERSION,
        prompt_template_version=_clean_str(
            prompt_template_version, field="prompt_template_version", max_len=64
        )
        or FIXTURE_PROMPT_TEMPLATE_VERSION,
        budget_tokens=budget_tokens if budget_tokens is not None else DEFAULT_BUDGET_TOKENS,
        budget_usd_cents=budget_usd_cents if budget_usd_cents is not None else DEFAULT_BUDGET_USD_CENTS,
        metadata_json={"data_mode": "fixture", "can_execute_orders": False},
        creation_idempotency_key=cleaned_key,
    )
    db.add(agent)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        if cleaned_key:
            existing = (
                db.query(Agent)
                .filter(
                    Agent.portfolio_id == portfolio_id,
                    Agent.creation_idempotency_key == cleaned_key,
                )
                .one_or_none()
            )
            if existing is not None:
                return _agent_out(existing)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Unable to create agent",
        ) from exc

    record_audit_event(
        db,
        actor_subject=subject.subject,
        action=AUDIT_AGENT_CREATE,
        resource_type="agent",
        resource_id=str(agent.id),
        metadata={
            "portfolio_id": str(portfolio_id),
            "name": agent.name,
            "status": agent.status,
            "idempotency_key": cleaned_key,
        },
    )
    db.commit()
    db.refresh(agent)
    return _agent_out(agent)


def get_agent(
    db: Session,
    subject: AuthenticatedSubject,
    portfolio_id: uuid.UUID,
    agent_id: uuid.UUID,
) -> AgentOut:
    return _agent_out(get_owned_agent(db, subject, portfolio_id, agent_id))


def patch_agent(
    db: Session,
    subject: AuthenticatedSubject,
    portfolio_id: uuid.UUID,
    agent_id: uuid.UUID,
    *,
    name: str | None = None,
    purpose: str | None = None,
    capabilities: list[str] | None = None,
    status_value: str | None = None,
    budget_tokens: int | None = None,
    budget_usd_cents: int | None = None,
) -> AgentOut:
    agent = get_owned_agent(db, subject, portfolio_id, agent_id)
    changed: dict[str, Any] = {}
    if name is not None:
        cleaned = _clean_str(name, field="name", max_len=128)
        if not cleaned:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Name is required")
        agent.name = cleaned
        changed["name"] = cleaned
    if purpose is not None:
        cleaned = _clean_str(purpose, field="purpose", max_len=2000)
        if not cleaned:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Purpose is required")
        agent.purpose = cleaned
        changed["purpose"] = cleaned
    if capabilities is not None:
        agent.capabilities_json = _clean_capabilities(capabilities)
        changed["capabilities"] = agent.capabilities_json
    if status_value is not None:
        cleaned_status = status_value.strip().lower()
        if cleaned_status not in ALLOWED_AGENT_STATUSES:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid agent status")
        agent.status = cleaned_status
        changed["status"] = cleaned_status
    if budget_tokens is not None:
        agent.budget_tokens = budget_tokens
        changed["budget_tokens"] = budget_tokens
    if budget_usd_cents is not None:
        agent.budget_usd_cents = budget_usd_cents
        changed["budget_usd_cents"] = budget_usd_cents

    if not changed:
        return _agent_out(agent)

    record_audit_event(
        db,
        actor_subject=subject.subject,
        action=AUDIT_AGENT_UPDATE,
        resource_type="agent",
        resource_id=str(agent.id),
        metadata={"portfolio_id": str(portfolio_id), "changed": changed},
    )
    db.commit()
    db.refresh(agent)
    return _agent_out(agent)


def _holdings_snapshot(db: Session, portfolio_id: uuid.UUID) -> list[dict[str, str]]:
    rows = list_positions(db, portfolio_id)
    return [
        {
            "symbol": pos.symbol,
            "quantity": qty_str(pos.quantity),
            "avg_cost": money_str(pos.avg_cost),
        }
        for pos in rows
        if qty(pos.quantity) > 0
    ]


def _build_facts_payload(
    *,
    portfolio_id: uuid.UUID,
    portfolio_version_id: uuid.UUID | None,
    data_as_of: datetime,
    holdings: list[dict[str, str]],
    cash: dict[str, Any],
    risk_inputs: dict[str, Any],
    evidence_refs: list[dict[str, str]],
) -> dict[str, Any]:
    return {
        "portfolio_id": str(portfolio_id),
        "portfolio_version_id": str(portfolio_version_id) if portfolio_version_id else None,
        "data_as_of": data_as_of.isoformat(),
        "evidence_refs": evidence_refs,
        "holdings": holdings,
        "cash": cash,
        "risk_inputs": risk_inputs,
    }


def create_facts_packet(
    db: Session,
    subject: AuthenticatedSubject,
    portfolio_id: uuid.UUID,
    *,
    portfolio_version_id: uuid.UUID | None = None,
    idempotency_key: str | None = None,
) -> FactsPacketOut:
    portfolio = get_owned_portfolio(db, subject, portfolio_id)
    user_id = require_user_id(subject)
    cleaned_key = _clean_str(idempotency_key, field="Idempotency-Key", max_len=128)

    if cleaned_key:
        existing = (
            db.query(AgentFactsPacket)
            .filter(
                AgentFactsPacket.portfolio_id == portfolio_id,
                AgentFactsPacket.creation_idempotency_key == cleaned_key,
            )
            .one_or_none()
        )
        if existing is not None:
            return _facts_out(existing)

    version: PortfolioVersion | None = None
    if portfolio_version_id is not None:
        version = (
            db.query(PortfolioVersion)
            .filter(
                PortfolioVersion.id == portfolio_version_id,
                PortfolioVersion.portfolio_id == portfolio_id,
                PortfolioVersion.owner_user_id == user_id,
            )
            .one_or_none()
        )
        if version is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Portfolio version not found",
            )

    if portfolio.wallet is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Portfolio wallet is missing",
        )

    settings = get_settings()
    data_as_of = datetime.now(UTC)
    if version is not None:
        holdings = [
            {
                "symbol": str(item.get("symbol", "")),
                "quantity": str(item.get("quantity", "0")),
                "avg_cost": str(item.get("avg_cost", "0")),
            }
            for item in (version.holdings_json or [])
            if isinstance(item, dict)
        ]
        cash = dict(version.allocation_json or {})
        evidence_refs = [
            {
                "kind": "portfolio_version",
                "ref": str(version.id),
                "label": f"Version {version.version_number} checksum {version.checksum[:12]}",
            }
        ]
        risk_inputs = {
            "source": "portfolio_version",
            "version_checksum": version.checksum,
            "holdings_count": len(holdings),
            "quote_mode": getattr(settings, "quote_mode", "fixture"),
            "simulation_only": True,
            "plaid_excluded": True,
        }
        data_as_of = version.created_at if version.created_at.tzinfo else version.created_at.replace(tzinfo=UTC)
    else:
        holdings = _holdings_snapshot(db, portfolio_id)
        cash = {
            "cash_balance": money_str(portfolio.wallet.balance),
            "complimentary_balance": money_str(portfolio.wallet.complimentary_balance),
            "currency_code": portfolio.wallet.currency_code,
            "wallet_version": int(portfolio.wallet.version or 0),
        }
        evidence_refs = [
            {
                "kind": "portfolio_wallet",
                "ref": str(portfolio.wallet.id),
                "label": f"Live wallet version {portfolio.wallet.version}",
            },
            {
                "kind": "portfolio",
                "ref": str(portfolio.id),
                "label": portfolio.name,
            },
        ]
        risk_inputs = {
            "source": "live_portfolio",
            "holdings_count": len(holdings),
            "quote_mode": getattr(settings, "quote_mode", "fixture"),
            "simulation_only": True,
            "plaid_excluded": True,
            "concentration": (
                max((float(h["quantity"]) for h in holdings), default=0.0) if holdings else 0.0
            ),
        }

    payload = _build_facts_payload(
        portfolio_id=portfolio_id,
        portfolio_version_id=version.id if version else None,
        data_as_of=data_as_of,
        holdings=holdings,
        cash=cash,
        risk_inputs=risk_inputs,
        evidence_refs=evidence_refs,
    )
    checksum = _checksum(payload)

    packet = AgentFactsPacket(
        portfolio_id=portfolio_id,
        owner_user_id=user_id,
        portfolio_version_id=version.id if version else None,
        data_as_of=data_as_of,
        evidence_refs_json=evidence_refs,
        holdings_json=holdings,
        cash_json=cash,
        risk_inputs_json=risk_inputs,
        checksum=checksum,
        creation_idempotency_key=cleaned_key,
    )
    db.add(packet)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        if cleaned_key:
            existing = (
                db.query(AgentFactsPacket)
                .filter(
                    AgentFactsPacket.portfolio_id == portfolio_id,
                    AgentFactsPacket.creation_idempotency_key == cleaned_key,
                )
                .one_or_none()
            )
            if existing is not None:
                return _facts_out(existing)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Unable to create facts packet",
        ) from exc

    record_audit_event(
        db,
        actor_subject=subject.subject,
        action=AUDIT_FACTS_CREATE,
        resource_type="agent_facts_packet",
        resource_id=str(packet.id),
        metadata={
            "portfolio_id": str(portfolio_id),
            "checksum": checksum,
            "idempotency_key": cleaned_key,
        },
    )
    db.commit()
    db.refresh(packet)
    return _facts_out(packet)


def get_facts_packet(
    db: Session,
    subject: AuthenticatedSubject,
    portfolio_id: uuid.UUID,
    facts_packet_id: uuid.UUID,
) -> FactsPacketOut:
    return _facts_out(get_owned_facts_packet(db, subject, portfolio_id, facts_packet_id))


def _fixture_proposal_body(
    *,
    agent: Agent,
    packet: AgentFactsPacket,
    proposal_type: str,
    horizon: str,
) -> dict[str, Any]:
    holdings = [h for h in (packet.holdings_json or []) if isinstance(h, dict)]
    cash = dict(packet.cash_json or {})
    symbols = [str(h.get("symbol", "")) for h in holdings if h.get("symbol")]
    if proposal_type == PROPOSAL_TYPE_REBALANCE and symbols:
        focus = symbols[0]
        actions = [
            {
                "action": "review_trim",
                "symbol": focus,
                "quantity": None,
                "rationale": (
                    f"Fixture scenario suggests reviewing concentration in {focus} "
                    "before any simulated order preview."
                ),
            }
        ]
        summary = (
            f"Simulation scenario: review concentration in {focus} over a {horizon} horizon. "
            "No trade is placed."
        )
        draft_allocation = {
            "mode": "fixture",
            "focus_symbol": focus,
            "cash_balance": cash.get("cash_balance"),
            "holdings_count": len(holdings),
        }
    else:
        actions = [
            {
                "action": "hold",
                "symbol": None,
                "quantity": None,
                "rationale": "Fixture scenario recommends holding current simulated positions.",
            }
        ]
        summary = (
            f"Simulation scenario: hold current simulated allocation over a {horizon} horizon. "
            "No trade is placed."
        )
        draft_allocation = {
            "mode": "fixture",
            "recommendation": "hold",
            "cash_balance": cash.get("cash_balance"),
            "holdings_count": len(holdings),
        }

    assumptions = [
        "Authorized portfolio facts only; no external market inference.",
        f"Data mode is fixture ({agent.model_provider}/{agent.model_name}).",
        "Agent cannot confirm or execute simulated orders.",
        "Plaid and production broker data are excluded.",
    ]
    limitations = (
        "Deterministic fixture output for review only. Missing live market context, "
        "no certainty claim, and no authority to mutate ledger or orders."
    )
    return {
        "proposal_type": proposal_type,
        "horizon": horizon,
        "assumptions": assumptions,
        "actions": actions,
        "draft_allocation": draft_allocation,
        "evidence_refs": list(packet.evidence_refs_json or []),
        "confidence": "low",
        "limitations": limitations,
        "safety_decision": SAFETY_DECISION_ALLOWED,
        "summary": summary,
        "cost_usd_cents": 0,
        "latency_ms": 1,
    }


def generate_proposal(
    db: Session,
    subject: AuthenticatedSubject,
    portfolio_id: uuid.UUID,
    agent_id: uuid.UUID,
    *,
    facts_packet_id: uuid.UUID | None = None,
    proposal_type: str | None = None,
    horizon: str | None = None,
    idempotency_key: str | None = None,
) -> ProposalOut:
    agent = get_owned_agent(db, subject, portfolio_id, agent_id)
    if agent.status != AGENT_STATUS_ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Agent must be active to generate proposals",
        )
    cleaned_key = _clean_str(idempotency_key, field="Idempotency-Key", max_len=128)

    if cleaned_key:
        existing = (
            db.query(AgentProposal)
            .filter(
                AgentProposal.agent_id == agent_id,
                AgentProposal.creation_idempotency_key == cleaned_key,
            )
            .one_or_none()
        )
        if existing is not None:
            return _proposal_out(existing, agent_name=agent.name)

    if facts_packet_id is not None:
        packet = get_owned_facts_packet(db, subject, portfolio_id, facts_packet_id)
    else:
        packet_out = create_facts_packet(
            db,
            subject,
            portfolio_id,
            idempotency_key=f"auto-facts:{cleaned_key}" if cleaned_key else None,
        )
        packet = get_owned_facts_packet(
            db, subject, portfolio_id, uuid.UUID(packet_out.id)
        )

    cleaned_type = (proposal_type or "").strip().lower() or (
        PROPOSAL_TYPE_REBALANCE
        if any(isinstance(h, dict) and h.get("symbol") for h in (packet.holdings_json or []))
        else PROPOSAL_TYPE_HOLD
    )
    if cleaned_type not in ALLOWED_PROPOSAL_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid proposal type")
    cleaned_horizon = _clean_str(horizon, field="horizon", max_len=64) or "30d"

    body = _fixture_proposal_body(
        agent=agent,
        packet=packet,
        proposal_type=cleaned_type,
        horizon=cleaned_horizon,
    )

    proposal = AgentProposal(
        agent_id=agent.id,
        portfolio_id=portfolio_id,
        owner_user_id=agent.owner_user_id,
        facts_packet_id=packet.id,
        facts_checksum=packet.checksum,
        proposal_type=body["proposal_type"],
        horizon=body["horizon"],
        assumptions_json=body["assumptions"],
        actions_json=body["actions"],
        draft_allocation_json=body["draft_allocation"],
        evidence_refs_json=body["evidence_refs"],
        confidence=body["confidence"],
        limitations=body["limitations"],
        safety_decision=body["safety_decision"],
        model_provider=agent.model_provider,
        model_name=agent.model_name,
        model_version=agent.model_version,
        prompt_template_version=agent.prompt_template_version,
        cost_usd_cents=body["cost_usd_cents"],
        latency_ms=body["latency_ms"],
        status=PROPOSAL_STATUS_READY_FOR_REVIEW,
        summary=body["summary"],
        data_as_of=packet.data_as_of,
        creation_idempotency_key=cleaned_key,
    )
    db.add(proposal)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        if cleaned_key:
            existing = (
                db.query(AgentProposal)
                .filter(
                    AgentProposal.agent_id == agent_id,
                    AgentProposal.creation_idempotency_key == cleaned_key,
                )
                .one_or_none()
            )
            if existing is not None:
                return _proposal_out(existing, agent_name=agent.name)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Unable to create proposal",
        ) from exc

    record_audit_event(
        db,
        actor_subject=subject.subject,
        action=AUDIT_PROPOSAL_CREATE,
        resource_type="agent_proposal",
        resource_id=str(proposal.id),
        metadata={
            "portfolio_id": str(portfolio_id),
            "agent_id": str(agent_id),
            "facts_checksum": packet.checksum,
            "proposal_type": proposal.proposal_type,
            "safety_decision": proposal.safety_decision,
            "idempotency_key": cleaned_key,
            "can_execute": False,
        },
    )
    db.commit()
    db.refresh(proposal)
    return _proposal_out(proposal, agent_name=agent.name)


def list_proposals(
    db: Session,
    subject: AuthenticatedSubject,
    portfolio_id: uuid.UUID,
) -> ProposalListOut:
    get_owned_portfolio(db, subject, portfolio_id)
    user_id = require_user_id(subject)
    rows = (
        db.query(AgentProposal, Agent.name)
        .join(Agent, Agent.id == AgentProposal.agent_id)
        .filter(
            AgentProposal.portfolio_id == portfolio_id,
            AgentProposal.owner_user_id == user_id,
        )
        .order_by(AgentProposal.created_at.desc())
        .all()
    )
    return ProposalListOut(
        proposals=[_proposal_out(proposal, agent_name=name) for proposal, name in rows]
    )


def get_proposal(
    db: Session,
    subject: AuthenticatedSubject,
    portfolio_id: uuid.UUID,
    proposal_id: uuid.UUID,
) -> ProposalOut:
    proposal = get_owned_proposal(db, subject, portfolio_id, proposal_id)
    agent = get_owned_agent(db, subject, portfolio_id, proposal.agent_id)
    return _proposal_out(proposal, agent_name=agent.name)


def get_proposal_global(
    db: Session,
    subject: AuthenticatedSubject,
    proposal_id: uuid.UUID,
) -> ProposalOut:
    proposal = get_owned_proposal_by_id(db, subject, proposal_id)
    agent = (
        db.query(Agent)
        .filter(Agent.id == proposal.agent_id, Agent.owner_user_id == proposal.owner_user_id)
        .one()
    )
    return _proposal_out(proposal, agent_name=agent.name)


def patch_proposal_status(
    db: Session,
    subject: AuthenticatedSubject,
    portfolio_id: uuid.UUID,
    proposal_id: uuid.UUID,
    *,
    status_value: str,
) -> ProposalOut:
    """Lifecycle status only — never mutates proposal content or trading state."""
    proposal = get_owned_proposal(db, subject, portfolio_id, proposal_id)
    agent = get_owned_agent(db, subject, portfolio_id, proposal.agent_id)
    cleaned = status_value.strip().lower()
    if cleaned not in ALLOWED_PROPOSAL_STATUSES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid proposal status")
    if cleaned == proposal.status:
        return _proposal_out(proposal, agent_name=agent.name)

    previous = proposal.status
    proposal.status = cleaned
    record_audit_event(
        db,
        actor_subject=subject.subject,
        action=AUDIT_PROPOSAL_STATUS,
        resource_type="agent_proposal",
        resource_id=str(proposal.id),
        metadata={
            "portfolio_id": str(portfolio_id),
            "from": previous,
            "to": cleaned,
            "can_execute": False,
        },
    )
    db.commit()
    db.refresh(proposal)
    return _proposal_out(proposal, agent_name=agent.name)
