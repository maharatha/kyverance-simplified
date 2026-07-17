import Link from "next/link";
import { formatTimestamp, type AgentProposalSummary } from "@/lib/home";

type AgentProposalCardProps = {
  agent: AgentProposalSummary;
};

export function AgentProposalCard({ agent }: AgentProposalCardProps) {
  if (agent.status === "unavailable") {
    return (
      <section className="home-card" aria-labelledby="agent-card-heading">
        <h2 id="agent-card-heading">Agent brief</h2>
        <p className="home-agent-summary">
          {agent.summary ?? "Agent content is unavailable. Portfolio facts remain the source of truth when present."}
        </p>
      </section>
    );
  }

  const isProposal = agent.status === "proposal";

  return (
    <section className="home-card" aria-labelledby="agent-card-heading">
      <h2 id="agent-card-heading">{isProposal ? "Agent proposal" : "Agent brief"}</h2>
      <div className="home-card-meta">
        <span>{agent.agentName}</span>
        {agent.generatedAt ? <span>Generated {formatTimestamp(agent.generatedAt)}</span> : null}
        {typeof agent.evidenceCount === "number" ? (
          <span>{agent.evidenceCount} evidence items</span>
        ) : null}
        {agent.confidence ? (
          <span className="home-badge">Confidence: {agent.confidence}</span>
        ) : null}
      </div>

      {isProposal ? (
        <p className="home-agent-label" role="status">
          Scenario / draft — no trade placed
        </p>
      ) : (
        <p className="home-agent-label" role="status">
          Scenario framing — educational brief
        </p>
      )}

      {agent.summary ? <p className="home-agent-summary">{agent.summary}</p> : null}

      {agent.assumptions && agent.assumptions.length > 0 ? (
        <>
          <h3 style={{ marginTop: "1rem", fontSize: "0.95rem" }}>Assumptions</h3>
          <ul className="home-assumptions">
            {agent.assumptions.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </>
      ) : null}

      {agent.href ? (
        <div className="home-card-actions">
          <Link href={agent.href} className="btn-secondary">
            {isProposal ? "Open proposal" : "Open brief"}
          </Link>
        </div>
      ) : null}
    </section>
  );
}
