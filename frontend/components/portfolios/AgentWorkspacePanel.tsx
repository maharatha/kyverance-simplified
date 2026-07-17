"use client";

import { useCallback, useEffect, useId, useState } from "react";
import Link from "next/link";
import { formatTimestamp } from "@/lib/home/format";
import {
  createAgent,
  fetchAgents,
  fetchProposals,
  generateProposal,
  type AgentConfig,
  type AgentProposal,
} from "@/lib/agents-api";

type AgentWorkspacePanelProps = {
  portfolioId: string;
  accessToken: string | null;
};

function newKey(prefix: string): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return `${prefix}-${crypto.randomUUID()}`;
  }
  return `${prefix}-${Date.now()}`;
}

export function AgentWorkspacePanel({ portfolioId, accessToken }: AgentWorkspacePanelProps) {
  const nameId = useId();
  const purposeId = useId();
  const [agents, setAgents] = useState<AgentConfig[]>([]);
  const [proposals, setProposals] = useState<AgentProposal[]>([]);
  const [emptyAgents, setEmptyAgents] = useState("No agents yet.");
  const [emptyProposals, setEmptyProposals] = useState("No proposals yet.");
  const [name, setName] = useState("");
  const [purpose, setPurpose] = useState("");
  const [selectedAgentId, setSelectedAgentId] = useState<string | null>(null);
  const [selectedProposal, setSelectedProposal] = useState<AgentProposal | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [agentList, proposalList] = await Promise.all([
        fetchAgents(portfolioId, { accessToken }),
        fetchProposals(portfolioId, { accessToken }),
      ]);
      setAgents(agentList.agents);
      setEmptyAgents(agentList.empty_state);
      setProposals(proposalList.proposals);
      setEmptyProposals(proposalList.empty_state);
      setSelectedAgentId((current) => current ?? agentList.agents[0]?.id ?? null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load agent workspace");
      setAgents([]);
      setProposals([]);
    } finally {
      setLoading(false);
    }
  }, [accessToken, portfolioId]);

  useEffect(() => {
    void load();
  }, [load]);

  async function onCreateAgent(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const agent = await createAgent(
        portfolioId,
        { name: name.trim(), purpose: purpose.trim(), capabilities: ["research", "scenario"] },
        { accessToken, idempotencyKey: newKey("agent") },
      );
      setName("");
      setPurpose("");
      setSelectedAgentId(agent.id);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to create agent");
    } finally {
      setBusy(false);
    }
  }

  async function onGenerateProposal() {
    if (!selectedAgentId) {
      setError("Create an agent before generating a proposal.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const proposal = await generateProposal(
        portfolioId,
        selectedAgentId,
        { horizon: "30d" },
        { accessToken, idempotencyKey: newKey("proposal") },
      );
      setSelectedProposal(proposal);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to generate proposal");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="portfolio-panel" aria-label="Agent workspace">
      <h2 className="portfolio-title" style={{ fontSize: "1.25rem" }}>
        Agent workspace
      </h2>
      <p className="portfolio-meta">
        Private agent configurations and deterministic fixture proposals. Agents can draft
        scenarios only — they cannot confirm or execute orders.
      </p>

      {loading ? (
        <p className="portfolio-status" role="status">
          Loading agents…
        </p>
      ) : null}
      {error ? (
        <p className="portfolio-error" role="alert">
          {error}
        </p>
      ) : null}

      <form className="portfolio-form" onSubmit={onCreateAgent}>
        <label className="portfolio-label" htmlFor={nameId}>
          Agent name
          <input
            id={nameId}
            className="portfolio-input"
            value={name}
            onChange={(event) => setName(event.target.value)}
            maxLength={128}
            required
            disabled={busy}
          />
        </label>
        <label className="portfolio-label" htmlFor={purposeId}>
          Purpose
          <textarea
            id={purposeId}
            className="portfolio-textarea"
            value={purpose}
            onChange={(event) => setPurpose(event.target.value)}
            maxLength={2000}
            required
            disabled={busy}
          />
        </label>
        <button type="submit" className="btn-secondary" disabled={busy || !name.trim() || !purpose.trim()}>
          Create agent
        </button>
      </form>

      <div className="portfolio-panel" style={{ borderTop: "none", paddingTop: "0.5rem" }}>
        <h3 className="portfolio-title" style={{ fontSize: "1.05rem" }}>
          Agents
        </h3>
        {agents.length === 0 ? (
          <p className="portfolio-empty" role="status">
            {emptyAgents}
          </p>
        ) : (
          <ul className="portfolio-list">
            {agents.map((agent) => (
              <li key={agent.id} className="portfolio-ledger-row">
                <button
                  type="button"
                  className={selectedAgentId === agent.id ? "btn-primary" : "btn-secondary"}
                  onClick={() => setSelectedAgentId(agent.id)}
                  disabled={busy}
                >
                  {agent.name}
                </button>
                <span className="portfolio-meta">
                  {agent.status} · {agent.model_provider}/{agent.model_name}@{agent.model_version}
                </span>
                <span className="portfolio-meta">{agent.purpose}</span>
              </li>
            ))}
          </ul>
        )}
        <button
          type="button"
          className="btn-secondary"
          style={{ marginTop: "0.85rem" }}
          onClick={() => void onGenerateProposal()}
          disabled={busy || !selectedAgentId}
        >
          Generate fixture proposal
        </button>
      </div>

      <div className="portfolio-panel">
        <h3 className="portfolio-title" style={{ fontSize: "1.05rem" }}>
          Proposals
        </h3>
        {proposals.length === 0 ? (
          <p className="portfolio-empty" role="status">
            {emptyProposals}
          </p>
        ) : (
          <ul className="portfolio-list">
            {proposals.map((proposal) => (
              <li key={proposal.id} className="portfolio-ledger-row">
                <strong className="portfolio-balance">{proposal.scenario_label}</strong>
                <span className="portfolio-meta">
                  {proposal.agent_name} · {proposal.proposal_type} · {proposal.horizon}
                </span>
                <span className="portfolio-meta">
                  Data as of {formatTimestamp(proposal.data_as_of)} · confidence {proposal.confidence}
                </span>
                <button
                  type="button"
                  className="btn-primary"
                  onClick={() => setSelectedProposal(proposal)}
                >
                  {proposal.review_cta}
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      {selectedProposal ? (
        <article className="portfolio-panel" aria-label="Proposal review">
          <h3 className="portfolio-title" style={{ fontSize: "1.05rem" }}>
            Review proposal
          </h3>
          <p className="portfolio-notice" role="status">
            {selectedProposal.scenario_label} — {selectedProposal.disclosure}
          </p>
          <p className="portfolio-meta">
            Data as of {formatTimestamp(selectedProposal.data_as_of)} · model{" "}
            {selectedProposal.model_provider}/{selectedProposal.model_name}@
            {selectedProposal.model_version} · template {selectedProposal.prompt_template_version}
          </p>
          <p className="portfolio-meta">
            Safety: {selectedProposal.safety_decision} · facts checksum{" "}
            {selectedProposal.facts_checksum.slice(0, 12)}…
          </p>
          <p className="portfolio-lede">{selectedProposal.summary}</p>
          <h4 className="portfolio-title" style={{ fontSize: "0.95rem" }}>
            Assumptions
          </h4>
          <ul className="portfolio-list">
            {selectedProposal.assumptions.map((item) => (
              <li key={item} className="portfolio-meta">
                {item}
              </li>
            ))}
          </ul>
          <h4 className="portfolio-title" style={{ fontSize: "0.95rem" }}>
            Evidence
          </h4>
          <ul className="portfolio-list">
            {selectedProposal.evidence_refs.map((item) => (
              <li key={`${item.kind}-${item.ref}`} className="portfolio-meta">
                {item.label} ({item.kind})
              </li>
            ))}
          </ul>
          <h4 className="portfolio-title" style={{ fontSize: "0.95rem" }}>
            Horizon & uncertainty
          </h4>
          <p className="portfolio-meta">
            Horizon {selectedProposal.horizon} · confidence {selectedProposal.confidence}
          </p>
          <p className="portfolio-meta">{selectedProposal.limitations}</p>
          <p className="portfolio-notice" role="note">
            No Execute or Auto-trade action is available. Simulated order preview remains a
            separate manual portfolio step when you choose it later.
          </p>
          <Link
            href={`/agents/proposals/${selectedProposal.id}`}
            className="btn-secondary"
            style={{ display: "inline-flex", marginTop: "0.75rem" }}
          >
            Open full review
          </Link>
        </article>
      ) : null}
    </section>
  );
}
