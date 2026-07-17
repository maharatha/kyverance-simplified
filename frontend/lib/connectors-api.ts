export type PlaidHolding = {
  id: string;
  symbol: string | null;
  name: string | null;
  quantity: string | number;
  currency: string;
  provenance: string;
  source_label: string;
};

export type PlaidAccount = {
  id: string;
  connection_id: string;
  name: string;
  mask: string | null;
  account_type: string | null;
  currency: string;
  provenance: string;
  source_label: string;
  last_synced_at: string | null;
  holdings: PlaidHolding[];
};

export type PlaidConnection = {
  id: string;
  provider_key: string;
  institution_name: string | null;
  status: string;
  last_synced_at: string | null;
  consent_recorded_at: string | null;
  disconnected_at: string | null;
  deletion_requested_at: string | null;
  accounts: PlaidAccount[];
};

export type ConnectorsOverview = {
  configured: boolean;
  plaid_configured: boolean;
  mode: "fake" | "plaid" | string;
  connect_consent_granted: boolean;
  data_retention_consent_granted: boolean;
  empty_state: string;
  connections: PlaidConnection[];
  message: string | null;
};

export type ConnectorRequestOptions = {
  accessToken?: string | null;
};

function apiBase(): string {
  return (process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000").replace(/\/$/, "");
}

function authHeaders(options?: ConnectorRequestOptions): HeadersInit {
  const headers: Record<string, string> = {};
  if (options?.accessToken) {
    headers.Authorization = `Bearer ${options.accessToken}`;
  }
  return headers;
}

async function parseJson<T>(response: Response): Promise<T> {
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail =
      typeof body === "object" && body && "detail" in body
        ? String((body as { detail: unknown }).detail)
        : `Request failed (${response.status})`;
    throw new Error(detail);
  }
  return body as T;
}

export async function fetchConnectorsOverview(
  options?: ConnectorRequestOptions,
): Promise<ConnectorsOverview> {
  const response = await fetch(`${apiBase()}/api/v1/connectors`, {
    credentials: "include",
    cache: "no-store",
    headers: authHeaders(options),
  });
  return parseJson<ConnectorsOverview>(response);
}

export async function setPlaidConsent(
  granted: boolean,
  options?: ConnectorRequestOptions,
): Promise<ConnectorsOverview> {
  const response = await fetch(`${apiBase()}/api/v1/connectors/plaid/consent`, {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(options),
    },
    body: JSON.stringify({ granted }),
  });
  return parseJson<ConnectorsOverview>(response);
}

export async function createPlaidLinkToken(
  options?: ConnectorRequestOptions,
): Promise<{ link_token: string; mode: string }> {
  const response = await fetch(`${apiBase()}/api/v1/connectors/plaid/link-token`, {
    method: "POST",
    credentials: "include",
    headers: authHeaders(options),
  });
  return parseJson(response);
}

export async function exchangePlaidToken(
  publicToken: string,
  providerKey = "any",
  options?: ConnectorRequestOptions,
): Promise<ConnectorsOverview> {
  const response = await fetch(`${apiBase()}/api/v1/connectors/plaid/exchange`, {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(options),
    },
    body: JSON.stringify({ public_token: publicToken, provider_key: providerKey }),
  });
  return parseJson<ConnectorsOverview>(response);
}

export async function fakeConnectPlaid(
  options?: ConnectorRequestOptions,
): Promise<ConnectorsOverview> {
  const response = await fetch(`${apiBase()}/api/v1/connectors/plaid/fake-connect`, {
    method: "POST",
    credentials: "include",
    headers: authHeaders(options),
  });
  return parseJson<ConnectorsOverview>(response);
}

export async function refreshConnection(
  connectionId: string,
  options?: ConnectorRequestOptions,
): Promise<ConnectorsOverview> {
  const response = await fetch(
    `${apiBase()}/api/v1/connectors/connections/${connectionId}/refresh`,
    { method: "POST", credentials: "include", headers: authHeaders(options) },
  );
  return parseJson<ConnectorsOverview>(response);
}

export async function disconnectConnection(
  connectionId: string,
  options?: ConnectorRequestOptions,
): Promise<ConnectorsOverview> {
  const response = await fetch(`${apiBase()}/api/v1/connectors/connections/${connectionId}`, {
    method: "DELETE",
    credentials: "include",
    headers: authHeaders(options),
  });
  return parseJson<ConnectorsOverview>(response);
}

export async function requestConnectionDeletion(
  connectionId: string,
  options?: ConnectorRequestOptions,
): Promise<{ status: string }> {
  const response = await fetch(
    `${apiBase()}/api/v1/connectors/connections/${connectionId}/deletion-request`,
    { method: "POST", credentials: "include", headers: authHeaders(options) },
  );
  return parseJson(response);
}
