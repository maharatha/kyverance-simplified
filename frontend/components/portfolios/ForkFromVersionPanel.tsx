"use client";

import { useId, useState } from "react";
import { useRouter } from "next/navigation";
import { forkPortfolioVersion } from "@/lib/portfolios-api";

type ForkFromVersionPanelProps = {
  accessToken: string | null;
};

function newKey(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return `fork-${crypto.randomUUID()}`;
  }
  return `fork-${Date.now()}`;
}

export function ForkFromVersionPanel({ accessToken }: ForkFromVersionPanelProps) {
  const router = useRouter();
  const versionIdInput = useId();
  const nameId = useId();
  const [versionId, setVersionId] = useState("");
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onFork(event: React.FormEvent) {
    event.preventDefault();
    const cleaned = versionId.trim();
    if (!cleaned) {
      setError("Published version ID is required");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const forked = await forkPortfolioVersion(
        cleaned,
        { name: name.trim() || null },
        { accessToken, idempotencyKey: newKey() },
      );
      router.push(`/portfolios/${forked.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to fork version");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="portfolio-panel" aria-label="Fork a public version">
      <h2 className="portfolio-title" style={{ fontSize: "1.25rem" }}>
        Fork a public version
      </h2>
      <p className="portfolio-meta">
        Creates a new private simulated portfolio from exactly one permitted public version. No
        sync, mirrored trades, payments, or Plaid data.
      </p>
      {error ? (
        <p className="portfolio-error" role="alert">
          {error}
        </p>
      ) : null}
      <form className="portfolio-form" onSubmit={onFork}>
        <label className="portfolio-label" htmlFor={versionIdInput}>
          Source version ID
          <input
            id={versionIdInput}
            className="portfolio-input"
            value={versionId}
            onChange={(e) => setVersionId(e.target.value)}
            required
            disabled={busy}
          />
        </label>
        <label className="portfolio-label" htmlFor={nameId}>
          Fork name (optional)
          <input
            id={nameId}
            className="portfolio-input"
            value={name}
            onChange={(e) => setName(e.target.value)}
            maxLength={128}
            disabled={busy}
          />
        </label>
        <button type="submit" className="btn-secondary" disabled={busy}>
          {busy ? "Forking…" : "Fork version"}
        </button>
      </form>
    </section>
  );
}
