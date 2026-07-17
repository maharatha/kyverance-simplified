"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  formatCursorSummary,
  formatDirtySummary,
  formatPreviewSummary,
} from "@/lib/delivery-status/serialize";
import type { DeliveryStatus } from "@/lib/delivery-status/types";
import "./delivery-status.css";

const REFRESH_MS = 4000;

type DeliveryStatusBoardProps = {
  initialStatus: DeliveryStatus;
  /** When false, skip polling (tests / production unavailable). */
  autoRefresh?: boolean;
};

export function DeliveryStatusBoard({
  initialStatus,
  autoRefresh = true,
}: DeliveryStatusBoardProps) {
  const [status, setStatus] = useState<DeliveryStatus>(initialStatus);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const response = await fetch("/api/delivery-status", {
        method: "GET",
        cache: "no-store",
      });
      const payload = (await response.json()) as DeliveryStatus;
      setStatus(payload);
      setError(null);
    } catch {
      setError("Could not refresh delivery status.");
    }
  }, []);

  useEffect(() => {
    if (!autoRefresh || !initialStatus.available) return;
    const id = window.setInterval(() => {
      void refresh();
    }, REFRESH_MS);
    return () => window.clearInterval(id);
  }, [autoRefresh, initialStatus.available, refresh]);

  if (!status.available) {
    return (
      <main className="delivery-status-page">
        <header className="delivery-status-header">
          <Link href="/" className="delivery-status-back">
            ← Home
          </Link>
          <h1>Delivery status</h1>
        </header>
        <section className="delivery-status-unavailable" aria-live="polite">
          <p>Unavailable outside local development.</p>
          <p className="delivery-status-muted">{status.reason}</p>
          <p className="delivery-status-muted">
            Last check: {new Date(status.checkedAt).toLocaleString()}
          </p>
        </section>
      </main>
    );
  }

  return (
    <main className="delivery-status-page">
      <header className="delivery-status-header">
        <div className="delivery-status-header-row">
          <Link href="/" className="delivery-status-back">
            ← Home
          </Link>
          <button type="button" className="btn-ghost delivery-status-refresh" onClick={() => void refresh()}>
            Refresh now
          </button>
        </div>
        <h1>Local delivery board</h1>
        <p className="delivery-status-muted">
          Auto-refreshes every {REFRESH_MS / 1000}s · Last check:{" "}
          <time dateTime={status.checkedAt}>
            {new Date(status.checkedAt).toLocaleString()}
          </time>
        </p>
        {error ? <p className="delivery-status-error">{error}</p> : null}
      </header>

      <div className="delivery-status-grid">
        <section aria-labelledby="delivery-branch">
          <h2 id="delivery-branch">Branch</h2>
          <p className="delivery-status-value">{status.branch}</p>
        </section>

        <section aria-labelledby="delivery-cursor">
          <h2 id="delivery-cursor">Cursor Agent process presence</h2>
          <p
            className="delivery-status-value"
            data-active={status.cursorCli.active ? "true" : "false"}
          >
            {formatCursorSummary(status)}
          </p>
        </section>

        <section aria-labelledby="delivery-preview">
          <h2 id="delivery-preview">Local preview</h2>
          <p
            className="delivery-status-value"
            data-healthy={status.preview.healthy ? "true" : "false"}
          >
            {formatPreviewSummary(status)}
          </p>
          <p className="delivery-status-muted">{status.preview.url}</p>
        </section>

        <section aria-labelledby="delivery-dirty">
          <h2 id="delivery-dirty">Working tree</h2>
          <p className="delivery-status-value">{formatDirtySummary(status.dirtyFiles)}</p>
          {status.dirtyFiles.length > 0 ? (
            <ul className="delivery-status-list">
              {status.dirtyFiles.map((file) => (
                <li key={file}>
                  <code>{file}</code>
                </li>
              ))}
            </ul>
          ) : null}
        </section>

        <section aria-labelledby="delivery-commits" className="delivery-status-span">
          <h2 id="delivery-commits">Latest commits</h2>
          <ul className="delivery-status-list">
            {status.commits.map((commit) => (
              <li key={commit.hash}>
                <code>{commit.hash}</code> {commit.subject}
                {commit.when ? (
                  <span className="delivery-status-muted"> · {commit.when}</span>
                ) : null}
              </li>
            ))}
          </ul>
        </section>

        <section aria-labelledby="delivery-recent" className="delivery-status-span">
          <h2 id="delivery-recent">Recent file activity</h2>
          <ul className="delivery-status-list">
            {status.recentFiles.map((file) => (
              <li key={`${file.path}-${file.modifiedAt}`}>
                <code>{file.path}</code>
                <span className="delivery-status-muted">
                  {" "}
                  · {new Date(file.modifiedAt).toLocaleString()}
                </span>
              </li>
            ))}
          </ul>
        </section>
      </div>
    </main>
  );
}
