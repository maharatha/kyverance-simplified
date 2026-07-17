"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useSession } from "next-auth/react";
import { formatTimestamp } from "@/lib/home/format";
import { fetchProposalById, type AgentProposal } from "@/lib/agents-api";
import "@/components/portfolios/portfolios.css";

type ProposalReviewClientProps = {
  proposalId: string;
};

export function ProposalReviewClient({ proposalId }: ProposalReviewClientProps) {
  const { data: session, status: authStatus } = useSession();
  const accessToken = session?.accessToken ?? null;
  const [proposal, setProposal] = useState<AgentProposal | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (authStatus === "loading") return;
    if (authStatus !== "authenticated" || session?.error) {
      setLoading(false);
      setProposal(null);
      setError(
        authStatus === "unauthenticated"
          ? "Sign in to review this proposal."
          : "Session expired. Sign in again to review this proposal.",
      );
      return;
    }

    let cancelled = false;
    setLoading(true);
    setError(null);
    void fetchProposalById(proposalId, { accessToken })
      .then((data) => {
        if (!cancelled) setProposal(data);
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setProposal(null);
          setError(err instanceof Error ? err.message : "Unable to load proposal");
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [accessToken, authStatus, proposalId, session?.error]);

  return (
    <main className="portfolio-page">
      <p className="portfolio-eyebrow">Agent proposal</p>
      <h1 className="portfolio-title">Review proposal</h1>

      {loading ? (
        <p className="portfolio-status" role="status">
          Loading proposal…
        </p>
      ) : null}
      {error ? (
        <p className="portfolio-error" role="alert">
          {error}
        </p>
      ) : null}

      {proposal ? (
        <>
          <p className="portfolio-notice" role="status">
            {proposal.scenario_label} — {proposal.disclosure}
          </p>
          <p className="portfolio-meta">
            Agent {proposal.agent_name} · {proposal.proposal_type} · horizon {proposal.horizon}
          </p>
          <p className="portfolio-meta">
            Data as of {formatTimestamp(proposal.data_as_of)} · model {proposal.model_provider}/
            {proposal.model_name}@{proposal.model_version}
          </p>
          <p className="portfolio-meta">
            Safety {proposal.safety_decision} · confidence {proposal.confidence} · facts{" "}
            {proposal.facts_checksum.slice(0, 16)}…
          </p>
          <p className="portfolio-lede">{proposal.summary}</p>

          <section className="portfolio-panel" aria-label="Assumptions">
            <h2 className="portfolio-title" style={{ fontSize: "1.15rem" }}>
              Assumptions
            </h2>
            <ul className="portfolio-list">
              {proposal.assumptions.map((item) => (
                <li key={item} className="portfolio-meta">
                  {item}
                </li>
              ))}
            </ul>
          </section>

          <section className="portfolio-panel" aria-label="Evidence">
            <h2 className="portfolio-title" style={{ fontSize: "1.15rem" }}>
              Evidence
            </h2>
            <ul className="portfolio-list">
              {proposal.evidence_refs.map((item) => (
                <li key={`${item.kind}-${item.ref}`} className="portfolio-meta">
                  {item.label}
                </li>
              ))}
            </ul>
          </section>

          <section className="portfolio-panel" aria-label="Limitations">
            <h2 className="portfolio-title" style={{ fontSize: "1.15rem" }}>
              Uncertainty and limitations
            </h2>
            <p className="portfolio-meta">{proposal.limitations}</p>
            <p className="portfolio-notice" role="note">
              This review cannot execute, auto-trade, confirm, or schedule orders.
            </p>
          </section>

          <Link href={`/portfolios/${proposal.portfolio_id}`} className="btn-secondary">
            Back to portfolio
          </Link>
        </>
      ) : null}
    </main>
  );
}
