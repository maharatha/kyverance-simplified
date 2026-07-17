"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useSession } from "next-auth/react";
import { formatMoney, formatTimestamp } from "@/lib/home/format";
import { fetchPortfolio, type PortfolioDetail } from "@/lib/portfolios-api";
import "./portfolios.css";

type PortfolioDetailClientProps = {
  portfolioId: string;
};

export function PortfolioDetailClient({ portfolioId }: PortfolioDetailClientProps) {
  const { data: session, status: authStatus } = useSession();
  const accessToken = session?.accessToken ?? null;
  const [data, setData] = useState<PortfolioDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const detail = await fetchPortfolio(portfolioId, { accessToken });
      setData(detail);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load portfolio");
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [accessToken, portfolioId]);

  useEffect(() => {
    if (authStatus === "loading") return;
    if (authStatus !== "authenticated" || session?.error) {
      setLoading(false);
      setData(null);
      setError(
        authStatus === "unauthenticated"
          ? "Sign in to open this portfolio."
          : "Session expired. Sign in again to open this portfolio.",
      );
      return;
    }
    void load();
  }, [authStatus, session?.error, load]);

  return (
    <main className="portfolio-page">
      <p className="portfolio-eyebrow">Portfolio workspace</p>
      {loading ? (
        <p className="portfolio-status" role="status">
          Loading portfolio…
        </p>
      ) : null}
      {error ? (
        <p className="portfolio-error" role="alert">
          {error}
        </p>
      ) : null}

      {data ? (
        <>
          <h1 className="portfolio-title">{data.name}</h1>
          {data.description ? <p className="portfolio-lede">{data.description}</p> : null}
          <p className="portfolio-notice">{data.simulation_notice}</p>

          <section className="portfolio-panel" aria-label="Wallet">
            <h2 className="portfolio-title" style={{ fontSize: "1.25rem" }}>
              Virtual wallet
            </h2>
            <p className="portfolio-balance">
              Cash: {formatMoney(data.wallet.cash_balance, data.wallet.currency_code)}
            </p>
            <p className="portfolio-meta">
              Complimentary:{" "}
              {formatMoney(data.wallet.complimentary_balance, data.wallet.currency_code)} · version{" "}
              {data.wallet.version}
            </p>
            <p className="portfolio-meta">
              {data.visibility} · {data.provenance} · {data.status}
            </p>
          </section>

          <section className="portfolio-panel" aria-label="Ledger">
            <h2 className="portfolio-title" style={{ fontSize: "1.25rem" }}>
              Ledger
            </h2>
            <p className="portfolio-meta">
              Immutable source records. Wallet cash is a projection of these entries.
            </p>
            <ul className="portfolio-ledger">
              {data.ledger.map((entry) => (
                <li key={entry.id} className="portfolio-ledger-row">
                  <strong className="portfolio-balance">
                    {formatMoney(entry.amount, entry.currency_code)}
                  </strong>
                  <span className="portfolio-meta">
                    {entry.source_type} · {entry.funding_bucket}
                  </span>
                  {entry.reason ? <span className="portfolio-meta">{entry.reason}</span> : null}
                  <span className="portfolio-meta">{formatTimestamp(entry.created_at)}</span>
                </li>
              ))}
            </ul>
          </section>
        </>
      ) : null}

      <Link className="portfolio-back" href="/portfolios">
        ← Back to portfolios
      </Link>
    </main>
  );
}
