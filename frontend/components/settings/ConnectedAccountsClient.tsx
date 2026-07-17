"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useSession } from "next-auth/react";
import {
  disconnectConnection,
  fakeConnectPlaid,
  fetchConnectorsOverview,
  refreshConnection,
  requestConnectionDeletion,
  setPlaidConsent,
  type ConnectorsOverview,
} from "@/lib/connectors-api";
import "./connected.css";

type ConnectedAccountsClientProps = {
  initialError?: string | null;
};

export function ConnectedAccountsClient({ initialError = null }: ConnectedAccountsClientProps) {
  const { data: session } = useSession();
  const accessToken = session?.accessToken ?? null;
  const [data, setData] = useState<ConnectorsOverview | null>(null);
  const [error, setError] = useState<string | null>(initialError);
  const [busy, setBusy] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const overview = await fetchConnectorsOverview({ accessToken });
      setData(overview);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load connected accounts");
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [accessToken]);

  useEffect(() => {
    void load();
  }, [load]);

  async function run(action: string, fn: () => Promise<ConnectorsOverview | { status: string }>) {
    setBusy(action);
    setError(null);
    try {
      const result = await fn();
      if ("connections" in result) {
        setData(result);
      } else {
        await load();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Action failed");
    } finally {
      setBusy(null);
    }
  }

  const opts = { accessToken };

  return (
    <main className="connected-page">
      <p className="connected-eyebrow">Settings</p>
      <h1 className="connected-title">Connected Accounts</h1>
      <p className="connected-lede">
        Read-only account links stay private. They cannot fund orders, join simulations, or become
        public portfolios.
      </p>

      {loading ? <p className="connected-status" role="status">Loading connections…</p> : null}
      {error ? (
        <p className="connected-error" role="alert">
          {error}
        </p>
      ) : null}

      {data ? (
        <section className="connected-panel" aria-label="Connection overview">
          <p className="connected-meta">
            Mode: <strong>{data.mode}</strong>
            {data.plaid_configured ? " · Plaid credentials configured" : " · Local fake provider"}
          </p>
          {data.message ? <p className="connected-message">{data.message}</p> : null}

          {!data.connect_consent_granted ? (
            <div className="connected-actions">
              <p>
                Explicit consent is required before creating a Link token or exchanging a public
                token.
              </p>
              <button
                type="button"
                className="btn-primary"
                disabled={busy !== null}
                onClick={() => void run("consent", () => setPlaidConsent(true, opts))}
              >
                {busy === "consent" ? "Saving…" : "Grant read-only connect consent"}
              </button>
            </div>
          ) : null}

          {data.connect_consent_granted && data.connections.length === 0 ? (
            <div className="connected-actions">
              {data.mode === "fake" ? (
                <>
                  <p>No connections yet. Use the local fake provider to verify the read-only flow.</p>
                  <button
                    type="button"
                    className="btn-primary"
                    disabled={busy !== null}
                    onClick={() => void run("connect", () => fakeConnectPlaid(opts))}
                  >
                    {busy === "connect" ? "Connecting…" : "Connect sample read-only account"}
                  </button>
                </>
              ) : data.plaid_configured ? (
                <p>
                  Plaid Link UI arrives with live credentials. Server Link-token and exchange
                  endpoints are ready.
                </p>
              ) : (
                <p role="status">Connections unavailable until Plaid is configured.</p>
              )}
            </div>
          ) : null}

          {data.connections.length > 0 ? (
            <ul className="connected-list">
              {data.connections.map((connection) => (
                <li key={connection.id} className="connected-item">
                  <div className="connected-item-header">
                    <h2>{connection.institution_name || "Linked institution"}</h2>
                    <span className="connected-badge">{connection.status}</span>
                  </div>
                  <p className="connected-source">Source: Linked account (read-only)</p>
                  <ul className="connected-accounts">
                    {connection.accounts.map((account) => (
                      <li key={account.id}>
                        <strong>{account.name}</strong>
                        {account.mask ? ` ·••${account.mask}` : ""}
                        {account.account_type ? ` · ${account.account_type}` : ""}
                        <ul className="connected-holdings">
                          {account.holdings.map((holding) => (
                            <li key={holding.id}>
                              {holding.symbol || holding.name || "Holding"} · {holding.quantity}{" "}
                              {holding.currency}
                            </li>
                          ))}
                        </ul>
                      </li>
                    ))}
                  </ul>
                  {connection.status === "connected" ? (
                    <div className="connected-item-actions">
                      <button
                        type="button"
                        className="btn-secondary"
                        disabled={busy !== null}
                        onClick={() =>
                          void run("refresh", () => refreshConnection(connection.id, opts))
                        }
                      >
                        Refresh
                      </button>
                      <button
                        type="button"
                        className="btn-secondary"
                        disabled={busy !== null}
                        onClick={() =>
                          void run("disconnect", () => disconnectConnection(connection.id, opts))
                        }
                      >
                        Disconnect
                      </button>
                      <button
                        type="button"
                        className="btn-ghost"
                        disabled={busy !== null}
                        onClick={() =>
                          void run("delete", () =>
                            requestConnectionDeletion(connection.id, opts),
                          )
                        }
                      >
                        Request deletion
                      </button>
                    </div>
                  ) : null}
                </li>
              ))}
            </ul>
          ) : null}
        </section>
      ) : null}

      <p className="connected-footer">
        <Link href="/profile" className="btn-secondary">
          Back to profile
        </Link>
      </p>
    </main>
  );
}
