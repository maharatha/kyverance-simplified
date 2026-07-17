"use client";

import { useCallback, useEffect, useId, useState } from "react";
import {
  PUBLISH_DISCLOSURE,
  createPortfolioVersion,
  fetchPortfolioVersions,
  patchPortfolio,
  publishPortfolioVersion,
  type PortfolioDetail,
  type PortfolioVersion,
} from "@/lib/portfolios-api";

type VersionPublishPanelProps = {
  portfolioId: string;
  portfolio: PortfolioDetail;
  accessToken: string | null;
  onUpdated: () => void;
};

function newKey(prefix: string): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return `${prefix}-${crypto.randomUUID()}`;
  }
  return `${prefix}-${Date.now()}`;
}

export function VersionPublishPanel({
  portfolioId,
  portfolio,
  accessToken,
  onUpdated,
}: VersionPublishPanelProps) {
  const thesisId = useId();
  const agentId = useId();
  const [thesis, setThesis] = useState(portfolio.thesis ?? "");
  const [agentRef, setAgentRef] = useState(portfolio.agent_config_ref ?? "");
  const [versions, setVersions] = useState<PortfolioVersion[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [consent, setConsent] = useState(false);
  const [disclosure, setDisclosure] = useState(false);
  const [visibility, setVisibility] = useState("public");
  const [license, setLicense] = useState("public_fork_allowed");
  const [selectedVersionId, setSelectedVersionId] = useState<string | null>(null);

  const loadVersions = useCallback(async () => {
    try {
      const list = await fetchPortfolioVersions(portfolioId, { accessToken });
      setVersions(list.versions);
      setSelectedVersionId((current) => current ?? list.versions[0]?.id ?? null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load versions");
    }
  }, [accessToken, portfolioId]);

  useEffect(() => {
    setThesis(portfolio.thesis ?? "");
    setAgentRef(portfolio.agent_config_ref ?? "");
  }, [portfolio.thesis, portfolio.agent_config_ref]);

  useEffect(() => {
    void loadVersions();
  }, [loadVersions]);

  async function onSaveThesis(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await patchPortfolio(
        portfolioId,
        { thesis: thesis.trim() || null, agent_config_ref: agentRef.trim() || null },
        { accessToken },
      );
      onUpdated();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to save thesis");
    } finally {
      setBusy(false);
    }
  }

  async function onCreateVersion() {
    setBusy(true);
    setError(null);
    try {
      const version = await createPortfolioVersion(portfolioId, {
        accessToken,
        idempotencyKey: newKey("version"),
      });
      setSelectedVersionId(version.id);
      await loadVersions();
      onUpdated();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to create version");
    } finally {
      setBusy(false);
    }
  }

  async function onPublish(event: React.FormEvent) {
    event.preventDefault();
    if (!selectedVersionId) {
      setError("Create a version before publishing");
      return;
    }
    if (!consent) {
      setError("Explicit publish consent is required");
      return;
    }
    if (!disclosure) {
      setError("Disclosure acknowledgement is required");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await publishPortfolioVersion(
        portfolioId,
        selectedVersionId,
        {
          visibility,
          license,
          provenance: "simulated",
          consent_acknowledged: true,
          disclosure_acknowledged: true,
        },
        { accessToken },
      );
      setConsent(false);
      setDisclosure(false);
      await loadVersions();
      onUpdated();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to publish version");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="portfolio-panel" aria-label="Versions and publishing">
      <h2 className="portfolio-title" style={{ fontSize: "1.25rem" }}>
        Versions &amp; publish
      </h2>
      <p className="portfolio-meta">
        Versions are immutable snapshots. Publishing requires creator role, explicit consent, and
        simulated provenance. Forks never sync or mirror trades.
      </p>

      {error ? (
        <p className="portfolio-error" role="alert">
          {error}
        </p>
      ) : null}

      <form className="portfolio-form" onSubmit={onSaveThesis}>
        <label className="portfolio-label" htmlFor={thesisId}>
          Thesis / rules
          <textarea
            id={thesisId}
            className="portfolio-textarea"
            value={thesis}
            onChange={(e) => setThesis(e.target.value)}
            maxLength={8000}
            disabled={busy}
          />
        </label>
        <label className="portfolio-label" htmlFor={agentId}>
          Agent config reference (optional)
          <input
            id={agentId}
            className="portfolio-input"
            value={agentRef}
            onChange={(e) => setAgentRef(e.target.value)}
            maxLength={128}
            disabled={busy}
          />
        </label>
        <button type="submit" className="btn-secondary" disabled={busy}>
          Save thesis
        </button>
      </form>

      <div className="portfolio-form" style={{ marginTop: "1rem" }}>
        <button type="button" className="btn-primary" disabled={busy} onClick={() => void onCreateVersion()}>
          {busy ? "Working…" : "Create immutable version"}
        </button>
      </div>

      {versions.length > 0 ? (
        <ul className="portfolio-list" aria-label="Version history">
          {versions.map((version) => (
            <li key={version.id} className="portfolio-item">
              <div className="portfolio-item-header">
                <button
                  type="button"
                  className="portfolio-version-select"
                  onClick={() => setSelectedVersionId(version.id)}
                  aria-pressed={selectedVersionId === version.id}
                >
                  v{version.version_number} · {version.status}
                </button>
                <span className="portfolio-meta">{version.visibility}</span>
              </div>
              <p className="portfolio-meta">
                checksum {version.checksum.slice(0, 12)}… · holdings {version.holdings.length}
                {version.license ? ` · ${version.license}` : ""}
                {version.fork_allowed ? " · fork allowed" : ""}
              </p>
            </li>
          ))}
        </ul>
      ) : (
        <p className="portfolio-empty">No versions yet.</p>
      )}

      <form className="portfolio-form" onSubmit={onPublish} style={{ marginTop: "1rem" }}>
        <label className="portfolio-label">
          Publish visibility
          <select
            className="portfolio-input"
            value={visibility}
            onChange={(e) => setVisibility(e.target.value)}
            disabled={busy}
          >
            <option value="public">public</option>
            <option value="private">private</option>
          </select>
        </label>
        <label className="portfolio-label">
          License
          <select
            className="portfolio-input"
            value={license}
            onChange={(e) => setLicense(e.target.value)}
            disabled={busy}
          >
            <option value="public_fork_allowed">public_fork_allowed</option>
            <option value="view_only">view_only</option>
          </select>
        </label>
        <p className="portfolio-notice" role="note">
          {PUBLISH_DISCLOSURE}
        </p>
        <label className="portfolio-check">
          <input
            type="checkbox"
            checked={consent}
            onChange={(e) => setConsent(e.target.checked)}
            disabled={busy}
          />
          I consent to publish this simulated version with the selected visibility, provenance, and
          license. No Plaid data is included.
        </label>
        <label className="portfolio-check">
          <input
            type="checkbox"
            checked={disclosure}
            onChange={(e) => setDisclosure(e.target.checked)}
            disabled={busy}
          />
          I acknowledge the simulated-portfolio disclosure above.
        </label>
        <button
          type="submit"
          className="btn-primary"
          disabled={busy || !selectedVersionId || !consent || !disclosure}
        >
          Publish selected version
        </button>
      </form>
    </section>
  );
}
