export type EvidenceRef = {
  kind: string;
  ref: string;
  label: string;
};

export type HoldingFact = {
  symbol: string;
  quantity: string;
  avg_cost: string;
};

export type AgentConfig = {
  id: string;
  portfolio_id: string;
  name: string;
  purpose: string;
  capabilities: string[];
  status: string;
  model_provider: string;
  model_name: string;
  model_version: string;
  prompt_template_version: string;
  budget_tokens: number;
  budget_usd_cents: number;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
  can_execute_orders: boolean;
  disclosure: string;
};

export type AgentList = {
  agents: AgentConfig[];
  empty_state: string;
};

export type FactsPacket = {
  id: string;
  portfolio_id: string;
  portfolio_version_id: string | null;
  data_as_of: string;
  evidence_refs: EvidenceRef[];
  holdings: HoldingFact[];
  cash: Record<string, unknown>;
  risk_inputs: Record<string, unknown>;
  checksum: string;
  created_at: string;
  immutable: boolean;
};

export type ProposalAction = {
  action: string;
  symbol: string | null;
  quantity: string | null;
  rationale: string;
};

export type AgentProposal = {
  id: string;
  agent_id: string;
  agent_name: string;
  portfolio_id: string;
  facts_packet_id: string;
  facts_checksum: string;
  proposal_type: string;
  horizon: string;
  assumptions: string[];
  actions: ProposalAction[];
  draft_allocation: Record<string, unknown>;
  evidence_refs: EvidenceRef[];
  confidence: string;
  limitations: string;
  safety_decision: string;
  model_provider: string;
  model_name: string;
  model_version: string;
  prompt_template_version: string;
  cost_usd_cents: number;
  latency_ms: number;
  status: string;
  summary: string;
  data_as_of: string;
  created_at: string;
  disclosure: string;
  scenario_label: string;
  can_execute: boolean;
  can_auto_trade: boolean;
  review_cta: string;
};

export type ProposalList = {
  proposals: AgentProposal[];
  empty_state: string;
};

export type AgentRequestOptions = {
  accessToken?: string | null;
  idempotencyKey?: string;
};

function apiBase(): string {
  return (process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000").replace(/\/$/, "");
}

function authHeaders(options?: AgentRequestOptions, extra?: HeadersInit): HeadersInit {
  const headers: Record<string, string> = {
    ...(extra as Record<string, string> | undefined),
  };
  if (options?.accessToken) {
    headers.Authorization = `Bearer ${options.accessToken}`;
  }
  if (options?.idempotencyKey) {
    headers["Idempotency-Key"] = options.idempotencyKey;
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

export async function fetchAgents(
  portfolioId: string,
  options?: AgentRequestOptions,
): Promise<AgentList> {
  const response = await fetch(`${apiBase()}/api/v1/portfolios/${portfolioId}/agents`, {
    credentials: "include",
    cache: "no-store",
    headers: authHeaders(options),
  });
  return parseJson<AgentList>(response);
}

export async function createAgent(
  portfolioId: string,
  input: { name: string; purpose: string; capabilities?: string[] },
  options?: AgentRequestOptions,
): Promise<AgentConfig> {
  const response = await fetch(`${apiBase()}/api/v1/portfolios/${portfolioId}/agents`, {
    method: "POST",
    credentials: "include",
    headers: authHeaders(options, { "Content-Type": "application/json" }),
    body: JSON.stringify({
      name: input.name,
      purpose: input.purpose,
      capabilities: input.capabilities ?? [],
    }),
  });
  return parseJson<AgentConfig>(response);
}

export async function fetchProposals(
  portfolioId: string,
  options?: AgentRequestOptions,
): Promise<ProposalList> {
  const response = await fetch(`${apiBase()}/api/v1/portfolios/${portfolioId}/proposals`, {
    credentials: "include",
    cache: "no-store",
    headers: authHeaders(options),
  });
  return parseJson<ProposalList>(response);
}

export async function generateProposal(
  portfolioId: string,
  agentId: string,
  input?: { horizon?: string; proposal_type?: string; facts_packet_id?: string },
  options?: AgentRequestOptions,
): Promise<AgentProposal> {
  const response = await fetch(
    `${apiBase()}/api/v1/portfolios/${portfolioId}/agents/${agentId}/proposals`,
    {
      method: "POST",
      credentials: "include",
      headers: authHeaders(options, { "Content-Type": "application/json" }),
      body: JSON.stringify(input ?? {}),
    },
  );
  return parseJson<AgentProposal>(response);
}

export async function fetchProposal(
  portfolioId: string,
  proposalId: string,
  options?: AgentRequestOptions,
): Promise<AgentProposal> {
  const response = await fetch(
    `${apiBase()}/api/v1/portfolios/${portfolioId}/proposals/${proposalId}`,
    {
      credentials: "include",
      cache: "no-store",
      headers: authHeaders(options),
    },
  );
  return parseJson<AgentProposal>(response);
}

export async function fetchProposalById(
  proposalId: string,
  options?: AgentRequestOptions,
): Promise<AgentProposal> {
  const response = await fetch(`${apiBase()}/api/v1/agent-proposals/${proposalId}`, {
    credentials: "include",
    cache: "no-store",
    headers: authHeaders(options),
  });
  return parseJson<AgentProposal>(response);
}
