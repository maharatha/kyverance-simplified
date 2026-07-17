import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { createPortfolio, fetchPortfolio, fetchPortfolios } from "./portfolios-api";

describe("portfolios-api", () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(
          JSON.stringify({
            portfolios: [
              {
                id: "p1",
                name: "Core",
                description: null,
                visibility: "private",
                provenance: "simulated",
                status: "active",
                currency_code: "VUSD",
                cash_balance: "1000.0000",
                created_at: "2026-07-16T00:00:00Z",
                updated_at: "2026-07-16T00:00:00Z",
              },
            ],
            empty_state: "populated",
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
      ),
    );
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it("lists portfolios", async () => {
    const list = await fetchPortfolios({ accessToken: "tok" });
    expect(list.empty_state).toBe("populated");
    expect(list.portfolios[0]?.cash_balance).toBe("1000.0000");
    expect(globalThis.fetch).toHaveBeenCalled();
  });

  it("creates with idempotency key", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (_url: string, init?: RequestInit) => {
        expect(init?.method).toBe("POST");
        const headers = init?.headers as Record<string, string>;
        expect(headers["Idempotency-Key"]).toBe("abc");
        return new Response(
          JSON.stringify({
            id: "p2",
            name: "New",
            description: null,
            visibility: "private",
            provenance: "simulated",
            status: "active",
            currency_code: "VUSD",
            cash_balance: "1000.0000",
            created_at: "2026-07-16T00:00:00Z",
            updated_at: "2026-07-16T00:00:00Z",
            wallet: {
              id: "w1",
              cash_balance: "1000.0000",
              complimentary_balance: "1000.0000",
              currency_code: "VUSD",
              version: 1,
            },
            ledger: [],
            simulation_notice: "Simulated",
          }),
          { status: 201, headers: { "Content-Type": "application/json" } },
        );
      }),
    );
    const created = await createPortfolio(
      { name: "New" },
      { accessToken: "tok", idempotencyKey: "abc" },
    );
    expect(created.id).toBe("p2");
    expect(created.cash_balance).toBe("1000.0000");
  });

  it("reads portfolio detail", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(
          JSON.stringify({
            id: "p1",
            name: "Core",
            description: null,
            visibility: "private",
            provenance: "simulated",
            status: "active",
            currency_code: "VUSD",
            cash_balance: "1000.0000",
            created_at: "2026-07-16T00:00:00Z",
            updated_at: "2026-07-16T00:00:00Z",
            wallet: {
              id: "w1",
              cash_balance: "1000.0000",
              complimentary_balance: "1000.0000",
              currency_code: "VUSD",
              version: 1,
            },
            ledger: [
              {
                id: "l1",
                amount: "1000.0000",
                currency_code: "VUSD",
                source_type: "INITIAL_ALLOCATION",
                funding_bucket: "complimentary",
                reason: null,
                actor: "system",
                created_at: "2026-07-16T00:00:00Z",
                idempotency_key: "initial:p1",
              },
            ],
            simulation_notice: "Simulated",
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
      ),
    );
    const detail = await fetchPortfolio("p1");
    expect(detail.ledger[0]?.amount).toBe("1000.0000");
  });
});
