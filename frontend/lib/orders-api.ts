import { fetchPortfolio, type PortfolioDetail, type PortfolioRequestOptions } from "./portfolios-api";

export type QuoteMeta = {
  quote_id: string;
  quote_as_of: string;
  quote_received_at: string;
  provider: string;
  freshness_label: string;
  data_mode: string;
  execution_policy: string;
};

export type OrderPreview = {
  preview_id: string;
  portfolio_id: string;
  wallet_id: string;
  symbol: string;
  side: string;
  quantity: string;
  notional: string;
  quote_price: string;
  execution_price: string;
  slippage_bps: string;
  fee: string;
  cash_after: string;
  warnings: string[];
  expires_at: string;
  status: string;
  quote: QuoteMeta;
  disclosure: string;
};

export type OrderReceipt = {
  receipt_id: string;
  order_id: string;
  request_id: string;
  portfolio_id: string;
  status: string;
  symbol: string;
  side: string;
  quantity: string;
  notional: string;
  execution_price: string;
  fee: string;
  slippage_bps: string;
  ledger_entry_ids: string[];
  position_quantity: string;
  position_delta: string;
  cash_balance: string;
  quote: QuoteMeta;
  simulated_at: string | null;
  disclosure: string;
  created_at: string | null;
};

export type ActivityItem = {
  receipt_id: string;
  order_id: string;
  symbol: string;
  side: string;
  status: string;
  quantity: string;
  notional: string;
  created_at: string;
  disclosure: string;
};

export type Position = {
  symbol: string;
  quantity: string;
  avg_cost: string;
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

export async function previewOrder(
  portfolioId: string,
  input: { symbol: string; side: string; quantity?: string | null; notional?: string | null },
  options?: PortfolioRequestOptions,
): Promise<OrderPreview> {
  const response = await fetch(`${apiBase()}/api/v1/portfolios/${portfolioId}/orders/preview`, {
    method: "POST",
    credentials: "include",
    headers: authHeaders(options, { "Content-Type": "application/json" }),
    body: JSON.stringify({
      symbol: input.symbol,
      side: input.side,
      quantity: input.quantity || null,
      notional: input.notional || null,
    }),
  });
  return parseJson<OrderPreview>(response);
}

export async function confirmOrder(
  portfolioId: string,
  previewId: string,
  options?: PortfolioRequestOptions & { idempotencyKey: string },
): Promise<OrderReceipt> {
  if (!options?.idempotencyKey) {
    throw new Error("Idempotency key is required to confirm an order");
  }
  const response = await fetch(`${apiBase()}/api/v1/portfolios/${portfolioId}/orders/confirm`, {
    method: "POST",
    credentials: "include",
    headers: authHeaders(options, {
      "Content-Type": "application/json",
      "Idempotency-Key": options.idempotencyKey,
    }),
    body: JSON.stringify({ preview_id: previewId }),
  });
  return parseJson<OrderReceipt>(response);
}

export async function fetchActivity(
  portfolioId: string,
  options?: PortfolioRequestOptions,
): Promise<{ items: ActivityItem[] }> {
  const response = await fetch(`${apiBase()}/api/v1/portfolios/${portfolioId}/activity`, {
    credentials: "include",
    cache: "no-store",
    headers: authHeaders(options),
  });
  return parseJson<{ items: ActivityItem[] }>(response);
}

export async function fetchPositions(
  portfolioId: string,
  options?: PortfolioRequestOptions,
): Promise<{ positions: Position[] }> {
  const response = await fetch(`${apiBase()}/api/v1/portfolios/${portfolioId}/positions`, {
    credentials: "include",
    cache: "no-store",
    headers: authHeaders(options),
  });
  return parseJson<{ positions: Position[] }>(response);
}

export type { PortfolioDetail };
export { fetchPortfolio };
