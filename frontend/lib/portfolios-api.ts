export type LedgerEntry = {
  id: string;
  amount: string;
  currency_code: string;
  source_type: string;
  funding_bucket: string;
  reason: string | null;
  actor: string;
  created_at: string;
  idempotency_key: string | null;
};

export type Wallet = {
  id: string;
  cash_balance: string;
  complimentary_balance: string;
  currency_code: string;
  version: number;
};

export type ForkLineage = {
  id: string;
  source_portfolio_id: string;
  source_version_id: string;
  license: string;
  entitlement: string;
  sync_enabled: boolean;
  mirror_trades: boolean;
  forked_at: string;
};

export type PortfolioSummary = {
  id: string;
  name: string;
  description: string | null;
  thesis?: string | null;
  agent_config_ref?: string | null;
  visibility: string;
  provenance: string;
  status: string;
  currency_code: string;
  cash_balance: string;
  created_at: string;
  updated_at: string;
  fork_lineage?: ForkLineage | null;
};

export type PortfolioDetail = PortfolioSummary & {
  wallet: Wallet;
  ledger: LedgerEntry[];
  simulation_notice: string;
};

export type PortfolioList = {
  portfolios: PortfolioSummary[];
  empty_state: string;
};

export type HoldingSnapshot = {
  symbol: string;
  quantity: string;
  avg_cost: string;
};

export type PortfolioVersion = {
  id: string;
  portfolio_id: string;
  version_number: number;
  name: string;
  description: string | null;
  thesis: string | null;
  agent_config_ref: string | null;
  holdings: HoldingSnapshot[];
  allocation: Record<string, unknown>;
  data_context: Record<string, unknown>;
  checksum: string;
  status: string;
  visibility: string;
  provenance: string;
  license: string | null;
  disclosure: string | null;
  consent_acknowledged: boolean;
  consent_text_version: string | null;
  consent_at: string | null;
  published_at: string | null;
  created_at: string;
  fork_allowed: boolean;
  fork_notice: string | null;
};

export type PortfolioVersionList = {
  versions: PortfolioVersion[];
};

export type PortfolioRequestOptions = {
  accessToken?: string | null;
};

function apiBase(): string {
  return (process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000").replace(/\/$/, "");
}

function authHeaders(options?: PortfolioRequestOptions, extra?: HeadersInit): HeadersInit {
  const headers: Record<string, string> = {
    ...(extra as Record<string, string> | undefined),
  };
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

export async function fetchPortfolios(
  options?: PortfolioRequestOptions,
): Promise<PortfolioList> {
  const response = await fetch(`${apiBase()}/api/v1/portfolios`, {
    credentials: "include",
    cache: "no-store",
    headers: authHeaders(options),
  });
  return parseJson<PortfolioList>(response);
}

export async function fetchPortfolio(
  portfolioId: string,
  options?: PortfolioRequestOptions,
): Promise<PortfolioDetail> {
  const response = await fetch(`${apiBase()}/api/v1/portfolios/${portfolioId}`, {
    credentials: "include",
    cache: "no-store",
    headers: authHeaders(options),
  });
  return parseJson<PortfolioDetail>(response);
}

export async function createPortfolio(
  input: {
    name: string;
    description?: string | null;
    thesis?: string | null;
    agent_config_ref?: string | null;
  },
  options?: PortfolioRequestOptions & { idempotencyKey?: string },
): Promise<PortfolioDetail> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (options?.idempotencyKey) {
    headers["Idempotency-Key"] = options.idempotencyKey;
  }
  const response = await fetch(`${apiBase()}/api/v1/portfolios`, {
    method: "POST",
    credentials: "include",
    headers: authHeaders(options, headers),
    body: JSON.stringify({
      name: input.name,
      description: input.description ?? null,
      thesis: input.thesis ?? null,
      agent_config_ref: input.agent_config_ref ?? null,
    }),
  });
  return parseJson<PortfolioDetail>(response);
}

export async function patchPortfolio(
  portfolioId: string,
  input: {
    name?: string | null;
    description?: string | null;
    thesis?: string | null;
    agent_config_ref?: string | null;
  },
  options?: PortfolioRequestOptions,
): Promise<PortfolioDetail> {
  const response = await fetch(`${apiBase()}/api/v1/portfolios/${portfolioId}`, {
    method: "PATCH",
    credentials: "include",
    headers: authHeaders(options, { "Content-Type": "application/json" }),
    body: JSON.stringify(input),
  });
  return parseJson<PortfolioDetail>(response);
}

export async function fetchPortfolioVersions(
  portfolioId: string,
  options?: PortfolioRequestOptions,
): Promise<PortfolioVersionList> {
  const response = await fetch(`${apiBase()}/api/v1/portfolios/${portfolioId}/versions`, {
    credentials: "include",
    cache: "no-store",
    headers: authHeaders(options),
  });
  return parseJson<PortfolioVersionList>(response);
}

export async function createPortfolioVersion(
  portfolioId: string,
  options?: PortfolioRequestOptions & { idempotencyKey?: string },
): Promise<PortfolioVersion> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (options?.idempotencyKey) {
    headers["Idempotency-Key"] = options.idempotencyKey;
  }
  const response = await fetch(`${apiBase()}/api/v1/portfolios/${portfolioId}/versions`, {
    method: "POST",
    credentials: "include",
    headers: authHeaders(options, headers),
    body: JSON.stringify({}),
  });
  return parseJson<PortfolioVersion>(response);
}

export async function publishPortfolioVersion(
  portfolioId: string,
  versionId: string,
  input: {
    visibility: string;
    license: string;
    provenance?: string;
    consent_acknowledged: boolean;
    disclosure_acknowledged?: boolean;
  },
  options?: PortfolioRequestOptions,
): Promise<PortfolioVersion> {
  const response = await fetch(
    `${apiBase()}/api/v1/portfolios/${portfolioId}/versions/${versionId}/publish`,
    {
      method: "POST",
      credentials: "include",
      headers: authHeaders(options, { "Content-Type": "application/json" }),
      body: JSON.stringify({
        visibility: input.visibility,
        license: input.license,
        provenance: input.provenance ?? "simulated",
        consent_acknowledged: input.consent_acknowledged,
        disclosure_acknowledged: input.disclosure_acknowledged ?? true,
      }),
    },
  );
  return parseJson<PortfolioVersion>(response);
}

export async function fetchPortfolioVersion(
  versionId: string,
  options?: PortfolioRequestOptions,
): Promise<PortfolioVersion> {
  const response = await fetch(`${apiBase()}/api/v1/portfolio-versions/${versionId}`, {
    credentials: "include",
    cache: "no-store",
    headers: authHeaders(options),
  });
  return parseJson<PortfolioVersion>(response);
}

export async function forkPortfolioVersion(
  versionId: string,
  input?: { name?: string | null },
  options?: PortfolioRequestOptions & { idempotencyKey?: string },
): Promise<PortfolioDetail> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (options?.idempotencyKey) {
    headers["Idempotency-Key"] = options.idempotencyKey;
  }
  const response = await fetch(`${apiBase()}/api/v1/portfolio-versions/${versionId}/fork`, {
    method: "POST",
    credentials: "include",
    headers: authHeaders(options, headers),
    body: JSON.stringify({ name: input?.name ?? null }),
  });
  return parseJson<PortfolioDetail>(response);
}
