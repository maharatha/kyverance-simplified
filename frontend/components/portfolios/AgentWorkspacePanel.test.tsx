import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AgentWorkspacePanel } from "./AgentWorkspacePanel";

const fetchAgents = vi.fn();
const fetchProposals = vi.fn();
const createAgent = vi.fn();
const generateProposal = vi.fn();

vi.mock("@/lib/agents-api", () => ({
  fetchAgents: (...args: unknown[]) => fetchAgents(...args),
  fetchProposals: (...args: unknown[]) => fetchProposals(...args),
  createAgent: (...args: unknown[]) => createAgent(...args),
  generateProposal: (...args: unknown[]) => generateProposal(...args),
}));

vi.mock("@/lib/home/format", () => ({
  formatTimestamp: (value: string) => `ts:${value}`,
}));

const sampleAgent = {
  id: "agent-1",
  portfolio_id: "pf-1",
  name: "Research scout",
  purpose: "Draft scenarios",
  capabilities: ["research"],
  status: "active",
  model_provider: "fixture",
  model_name: "deterministic-v1",
  model_version: "1.0.0",
  prompt_template_version: "agent-01-v1",
  budget_tokens: 8000,
  budget_usd_cents: 0,
  metadata: {},
  created_at: "2026-07-17T12:00:00Z",
  updated_at: "2026-07-17T12:00:00Z",
  can_execute_orders: false,
  disclosure: "simulation scenario",
};

const sampleProposal = {
  id: "prop-1",
  agent_id: "agent-1",
  agent_name: "Research scout",
  portfolio_id: "pf-1",
  facts_packet_id: "facts-1",
  facts_checksum: "abc123checksumvalue000000000000000000000000000000000000000000",
  proposal_type: "hold_scenario",
  horizon: "30d",
  assumptions: ["Authorized portfolio facts only"],
  actions: [{ action: "hold", symbol: null, quantity: null, rationale: "Hold" }],
  draft_allocation: { mode: "fixture" },
  evidence_refs: [{ kind: "portfolio", ref: "pf-1", label: "Portfolio wallet" }],
  confidence: "low",
  limitations: "Fixture only",
  safety_decision: "allowed_for_review",
  model_provider: "fixture",
  model_name: "deterministic-v1",
  model_version: "1.0.0",
  prompt_template_version: "agent-01-v1",
  cost_usd_cents: 0,
  latency_ms: 1,
  status: "ready_for_review",
  summary: "Simulation scenario: hold current allocation.",
  data_as_of: "2026-07-17T12:00:00Z",
  created_at: "2026-07-17T12:05:00Z",
  disclosure: "This is a simulation scenario / draft proposal.",
  scenario_label: "Simulation scenario",
  can_execute: false,
  can_auto_trade: false,
  review_cta: "Review proposal",
};

describe("AgentWorkspacePanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows empty states without execute or auto-trade controls", async () => {
    fetchAgents.mockResolvedValue({
      agents: [],
      empty_state: "No agents yet. Create a private agent configuration for this portfolio.",
    });
    fetchProposals.mockResolvedValue({
      proposals: [],
      empty_state: "No proposals yet. Generate a deterministic fixture proposal to review.",
    });

    render(<AgentWorkspacePanel portfolioId="pf-1" accessToken="token" />);

    expect(await screen.findByText(/No agents yet/i)).toBeInTheDocument();
    expect(screen.getByText(/No proposals yet/i)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /execute/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /auto-trade/i })).not.toBeInTheDocument();
    expect(screen.queryByText(/auto-trade/i)).not.toBeInTheDocument();
  });

  it("lists agents/proposals and reviews required forecast disclosures", async () => {
    fetchAgents.mockResolvedValue({ agents: [sampleAgent], empty_state: "" });
    fetchProposals.mockResolvedValue({ proposals: [sampleProposal], empty_state: "" });
    generateProposal.mockResolvedValue(sampleProposal);

    render(<AgentWorkspacePanel portfolioId="pf-1" accessToken="token" />);

    expect(await screen.findByRole("button", { name: /Research scout/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Review proposal/i })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Generate fixture proposal/i }));
    await waitFor(() => expect(generateProposal).toHaveBeenCalled());

    fireEvent.click(screen.getByRole("button", { name: /Review proposal/i }));
    const review = await screen.findByLabelText(/Proposal review/i);
    expect(within(review).getAllByText(/Simulation scenario/i).length).toBeGreaterThan(0);
    expect(within(review).getByText(/Data as of/i)).toBeInTheDocument();
    expect(within(review).getByText(/Authorized portfolio facts only/i)).toBeInTheDocument();
    expect(within(review).getByText(/Portfolio wallet/i)).toBeInTheDocument();
    expect(within(review).getByText(/Fixture only/i)).toBeInTheDocument();
    expect(within(review).getByText(/fixture\/deterministic-v1@1.0.0/i)).toBeInTheDocument();
    expect(within(review).getByText(/allowed_for_review/i)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /execute/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /auto-trade/i })).not.toBeInTheDocument();
  });

  it("creates an agent from the form", async () => {
    fetchAgents.mockResolvedValue({ agents: [], empty_state: "No agents yet." });
    fetchProposals.mockResolvedValue({ proposals: [], empty_state: "No proposals yet." });
    createAgent.mockResolvedValue(sampleAgent);

    render(<AgentWorkspacePanel portfolioId="pf-1" accessToken="token" />);
    await screen.findByText(/No agents yet/i);

    fireEvent.change(screen.getByLabelText(/Agent name/i), {
      target: { value: "Research scout" },
    });
    fireEvent.change(screen.getByLabelText(/Purpose/i), {
      target: { value: "Draft scenarios" },
    });

    fetchAgents.mockResolvedValue({ agents: [sampleAgent], empty_state: "" });
    fireEvent.click(screen.getByRole("button", { name: /Create agent/i }));

    await waitFor(() =>
      expect(createAgent).toHaveBeenCalledWith(
        "pf-1",
        expect.objectContaining({ name: "Research scout", purpose: "Draft scenarios" }),
        expect.objectContaining({ accessToken: "token" }),
      ),
    );
  });

  it("surfaces permission and load errors", async () => {
    fetchAgents.mockRejectedValue(new Error("Portfolio not found"));
    fetchProposals.mockRejectedValue(new Error("Portfolio not found"));

    render(<AgentWorkspacePanel portfolioId="missing" accessToken="token" />);

    expect(await screen.findByRole("alert")).toHaveTextContent("Portfolio not found");
  });
});
