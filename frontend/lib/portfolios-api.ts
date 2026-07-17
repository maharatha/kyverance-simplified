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

export type PortfolioSummary = {
  id: string;
  name: string;
  description: string | null;
  visibility: string;
  provenance: string;
  status: string;
  currency_code: string;
  cash_balance: string;
  created_at: string;
  updated_at: string;
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
  input: { name: string; description?: string | null },
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
    }),
  });
  return parseJson<PortfolioDetail>(response);
}
