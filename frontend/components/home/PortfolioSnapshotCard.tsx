"use client";

import { useId, useState } from "react";
import Link from "next/link";
import {
  formatMoney,
  formatSignedMoney,
  formatSignedPercent,
  formatTimestamp,
  provenanceLabel,
  type HomePortfolioSnapshot,
} from "@/lib/home";

type PortfolioSnapshotCardProps = {
  portfolio: HomePortfolioSnapshot;
};

export function PortfolioSnapshotCard({ portfolio }: PortfolioSnapshotCardProps) {
  const tableId = useId();
  const [showTable, setShowTable] = useState(false);
  const valuationUnavailable = portfolio.valuationStatus !== "available";
  const dayTone =
    portfolio.dayChange == null
      ? undefined
      : portfolio.dayChange.amount.startsWith("-")
        ? "down"
        : portfolio.dayChange.amount === "0" ||
            portfolio.dayChange.amount === "0.0" ||
            portfolio.dayChange.amount === "0.00"
          ? undefined
          : "up";

  return (
    <section className="home-card" aria-labelledby="portfolio-snapshot-heading">
      <h2 id="portfolio-snapshot-heading">{portfolio.name}</h2>
      <div className="home-card-meta">
        <span className="home-badge">{provenanceLabel(portfolio.provenance)}</span>
        <span>
          Valuation:{" "}
          {portfolio.valuationStatus === "available"
            ? "Available"
            : portfolio.valuationStatus === "stale"
              ? "Stale"
              : "Unavailable"}
        </span>
        <span>As of {formatTimestamp(portfolio.asOf)}</span>
      </div>

      {valuationUnavailable ? (
        <p className="home-support" style={{ marginTop: "1rem" }}>
          Valuation is {portfolio.valuationStatus}. Numeric totals are hidden so stale figures are
          not shown as current.
        </p>
      ) : (
        <dl className="home-metrics">
          <div className="home-metric">
            <dt>Total value</dt>
            <dd>{portfolio.totalValue ? formatMoney(portfolio.totalValue) : "—"}</dd>
          </div>
          <div className="home-metric">
            <dt>Cash</dt>
            <dd>{portfolio.cash ? formatMoney(portfolio.cash) : "—"}</dd>
          </div>
          {portfolio.dayChange ? (
            <div className="home-metric">
              <dt>Day change</dt>
              <dd data-tone={dayTone}>
                {formatSignedMoney(portfolio.dayChange.amount)}
                <span className="home-metric-note">
                  {dayTone === "down" ? "Down" : dayTone === "up" ? "Up" : "Unchanged"}{" "}
                  {formatSignedPercent(portfolio.dayChange.percent)}
                </span>
              </dd>
            </div>
          ) : null}
        </dl>
      )}

      {portfolio.allocation && portfolio.allocation.length > 0 ? (
        <div className="home-allocation">
          <h3>Allocation</h3>
          <div className="home-allocation-bars" aria-hidden={showTable}>
            {portfolio.allocation.map((slice) => (
              <div className="home-allocation-row" key={slice.label}>
                <span>{slice.label}</span>
                <div className="home-allocation-track">
                  <div
                    className="home-allocation-fill"
                    style={{ width: `${slice.weightPercent}%` }}
                  />
                </div>
                <span>{slice.weightPercent}%</span>
              </div>
            ))}
          </div>
          <button
            type="button"
            className="btn-ghost"
            aria-expanded={showTable}
            aria-controls={tableId}
            onClick={() => setShowTable((open) => !open)}
          >
            {showTable ? "Hide allocation table" : "View allocation as table"}
          </button>
          {showTable ? (
            <table id={tableId} className="home-allocation-table">
              <caption className="visually-hidden">Portfolio allocation percentages</caption>
              <thead>
                <tr>
                  <th scope="col">Sleeve</th>
                  <th scope="col">Weight</th>
                </tr>
              </thead>
              <tbody>
                {portfolio.allocation.map((slice) => (
                  <tr key={slice.label}>
                    <td>{slice.label}</td>
                    <td>{slice.weightPercent}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : null}
        </div>
      ) : null}

      <div className="home-card-actions">
        <Link href={portfolio.nextAction.href} className="btn-secondary">
          {portfolio.nextAction.label}
        </Link>
      </div>
    </section>
  );
}
