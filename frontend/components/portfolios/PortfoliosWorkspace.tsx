"use client";

import { useCallback, useEffect, useId, useState } from "react";
import Link from "next/link";
import { useSession } from "next-auth/react";
import { formatMoney } from "@/lib/home/format";
import {
  createPortfolio,
  fetchPortfolios,
  type PortfolioList,
  type PortfolioSummary,
} from "@/lib/portfolios-api";
import { ForkFromVersionPanel } from "./ForkFromVersionPanel";
import "./portfolios.css";

type PortfoliosWorkspaceProps = {
  initialError?: string | null;
};

function newIdempotencyKey(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `portfolio-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export function PortfoliosWorkspace({ initialError = null }: PortfoliosWorkspaceProps) {
  const { data: session, status: authStatus } = useSession();
  const accessToken = session?.accessToken ?? null;
  const nameId = useId();
  const descriptionId = useId();
  const [data, setData] = useState<PortfolioList | null>(null);
  const [error, setError] = useState<string | null>(initialError);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const list = await fetchPortfolios({ accessToken });
      setData(list);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load portfolios");
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [accessToken]);

  useEffect(() => {
    if (authStatus === "loading") return;
    if (authStatus !== "authenticated" || session?.error) {
      setLoading(false);
      setData(null);
      setError(
        authStatus === "unauthenticated"
          ? "Sign in to view your simulated portfolios."
          : "Session expired. Sign in again to view your portfolios.",
      );
      return;
    }
    void load();
  }, [authStatus, session?.error, load]);

  async function onCreate(event: React.FormEvent) {
    event.preventDefault();
    const trimmed = name.trim();
    if (!trimmed) {
      setError("Portfolio name is required");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await createPortfolio(
        { name: trimmed, description: description.trim() || null },
        { accessToken, idempotencyKey: newIdempotencyKey() },
      );
      setName("");
      setDescription("");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to create portfolio");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="portfolio-page">
      <p className="portfolio-eyebrow">Simulation</p>
      <h1 className="portfolio-title">Portfolios</h1>
      <p className="portfolio-lede">
        Each portfolio owns an isolated virtual wallet and immutable ledger. Cash never moves
        between portfolios. Simulated only — not a brokerage account.
      </p>

      {loading ? (
        <p className="portfolio-status" role="status">
          Loading portfolios…
        </p>
      ) : null}
      {error ? (
        <p className="portfolio-error" role="alert">
          {error}
        </p>
      ) : null}

      {authStatus === "authenticated" && !session?.error ? (
        <section className="portfolio-panel" aria-label="Create portfolio">
          <h2 className="portfolio-title" style={{ fontSize: "1.25rem" }}>
            Create portfolio
          </h2>
          <form className="portfolio-form" onSubmit={onCreate}>
            <label className="portfolio-label" htmlFor={nameId}>
              Name
              <input
                id={nameId}
                className="portfolio-input"
                value={name}
                onChange={(e) => setName(e.target.value)}
                maxLength={128}
                required
                disabled={busy}
              />
            </label>
            <label className="portfolio-label" htmlFor={descriptionId}>
              Description (optional)
              <textarea
                id={descriptionId}
                className="portfolio-textarea"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                maxLength={2000}
                disabled={busy}
              />
            </label>
            <button type="submit" className="btn-primary" disabled={busy}>
              {busy ? "Creating…" : "Create portfolio"}
            </button>
          </form>
        </section>
      ) : null}

      {authStatus === "authenticated" && !session?.error ? (
        <ForkFromVersionPanel accessToken={accessToken} />
      ) : null}

      {data ? (
        <section className="portfolio-panel" aria-label="Your portfolios">
          <p className="portfolio-meta">
            Provenance: simulated · Currency shown as virtual cash (VUSD)
          </p>
          {data.empty_state === "empty" ? (
            <p className="portfolio-empty">
              No portfolios yet. Create your first private simulated portfolio to receive an
              isolated practice wallet.
            </p>
          ) : (
            <ul className="portfolio-list">
              {data.portfolios.map((portfolio: PortfolioSummary) => (
                <li key={portfolio.id} className="portfolio-item">
                  <div className="portfolio-item-header">
                    <Link href={`/portfolios/${portfolio.id}`}>{portfolio.name}</Link>
                    <span className="portfolio-balance">
                      {formatMoney(portfolio.cash_balance, portfolio.currency_code)}
                    </span>
                  </div>
                  {portfolio.description ? (
                    <p className="portfolio-meta">{portfolio.description}</p>
                  ) : null}
                  <p className="portfolio-meta">
                    {portfolio.visibility} · {portfolio.provenance}
                    {portfolio.fork_lineage ? " · forked" : ""}
                  </p>
                </li>
              ))}
            </ul>
          )}
        </section>
      ) : null}
    </main>
  );
}
