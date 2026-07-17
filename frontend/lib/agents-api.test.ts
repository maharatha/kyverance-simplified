import { describe, expect, it, vi } from "vitest";
import {
  createAgent,
  fetchAgents,
  fetchProposalById,
  generateProposal,
} from "@/lib/agents-api";

describe("agents-api", () => {
  it("calls portfolio agent endpoints with auth and idempotency headers", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ agents: [], empty_state: "empty" }),
    });
    vi.stubGlobal("fetch", fetchMock);

    await fetchAgents("pf-1", { accessToken: "tok" });
    expect(fetchMock).toHaveBeenCalledWith(
      "http://127.0.0.1:8000/api/v1/portfolios/pf-1/agents",
      expect.objectContaining({
        headers: expect.objectContaining({ Authorization: "Bearer tok" }),
      }),
    );

    fetchMock.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ id: "a1", can_execute_orders: false }),
    });
    await createAgent(
      "pf-1",
      { name: "Scout", purpose: "Draft" },
      { accessToken: "tok", idempotencyKey: "k1" },
    );
    expect(fetchMock).toHaveBeenCalledWith(
      "http://127.0.0.1:8000/api/v1/portfolios/pf-1/agents",
      expect.objectContaining({
        method: "POST",
        headers: expect.objectContaining({
          Authorization: "Bearer tok",
          "Idempotency-Key": "k1",
        }),
      }),
    );

    fetchMock.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ id: "p1", can_execute: false, can_auto_trade: false }),
    });
    await generateProposal("pf-1", "a1", { horizon: "30d" }, { accessToken: "tok" });
    expect(fetchMock).toHaveBeenCalledWith(
      "http://127.0.0.1:8000/api/v1/portfolios/pf-1/agents/a1/proposals",
      expect.objectContaining({ method: "POST" }),
    );

    fetchMock.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ id: "p1", scenario_label: "Simulation scenario" }),
    });
    await fetchProposalById("p1", { accessToken: "tok" });
    expect(fetchMock).toHaveBeenCalledWith(
      "http://127.0.0.1:8000/api/v1/agent-proposals/p1",
      expect.anything(),
    );

    vi.unstubAllGlobals();
  });
});
