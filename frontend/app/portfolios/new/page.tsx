"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useSession } from "next-auth/react";
import { createPortfolio } from "@/lib/portfolios-api";
import "@/components/portfolios/portfolios.css";

function newIdempotencyKey(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `portfolio-new-${Date.now()}`;
}

export default function NewPortfolioPage() {
  const router = useRouter();
  const { data: session, status } = useSession();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (status === "unauthenticated") {
      router.replace("/sign-in");
    }
  }, [status, router]);

  async function onSubmit(event: React.FormEvent) {
    event.preventDefault();
    const trimmed = name.trim();
    if (!trimmed) {
      setError("Portfolio name is required");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const created = await createPortfolio(
        { name: trimmed, description: description.trim() || null },
        {
          accessToken: session?.accessToken ?? null,
          idempotencyKey: newIdempotencyKey(),
        },
      );
      router.replace(`/portfolios/${created.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to create portfolio");
      setBusy(false);
    }
  }

  if (status === "loading") {
    return (
      <main className="portfolio-page">
        <p className="portfolio-status" role="status">
          Loading…
        </p>
      </main>
    );
  }

  return (
    <main className="portfolio-page">
      <p className="portfolio-eyebrow">Simulation</p>
      <h1 className="portfolio-title">Create portfolio</h1>
      <p className="portfolio-lede">
        Creates a private simulated portfolio with an isolated virtual wallet and initial ledger
        credit.
      </p>
      {error ? (
        <p className="portfolio-error" role="alert">
          {error}
        </p>
      ) : null}
      <form className="portfolio-form portfolio-panel" onSubmit={onSubmit}>
        <label className="portfolio-label">
          Name
          <input
            className="portfolio-input"
            value={name}
            onChange={(e) => setName(e.target.value)}
            maxLength={128}
            required
            disabled={busy}
          />
        </label>
        <label className="portfolio-label">
          Description (optional)
          <textarea
            className="portfolio-textarea"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            maxLength={2000}
            disabled={busy}
          />
        </label>
        <button type="submit" className="btn-primary" disabled={busy || status !== "authenticated"}>
          {busy ? "Creating…" : "Create portfolio"}
        </button>
      </form>
    </main>
  );
}
