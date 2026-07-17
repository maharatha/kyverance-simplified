import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { confirmOrder, previewOrder } from "./orders-api";

describe("orders-api", () => {
  const originalFetch = globalThis.fetch;

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it("posts preview without placing an order", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string, init?: RequestInit) => {
        expect(String(url)).toContain("/orders/preview");
        expect(init?.method).toBe("POST");
        return new Response(
          JSON.stringify({
            preview_id: "prev-1",
            portfolio_id: "p1",
            wallet_id: "w1",
            symbol: "AAPL",
            side: "buy",
            quantity: "1.0000000000",
            notional: "190.0950",
            quote_price: "190.0000",
            execution_price: "190.0950",
            slippage_bps: "5.0000",
            fee: "0.0000",
            cash_after: "809.9050",
            warnings: [],
            expires_at: "2026-07-16T00:01:00Z",
            status: "open",
            quote: {
              quote_id: "fixture:AAPL:x",
              quote_as_of: "2026-07-16T00:00:00Z",
              quote_received_at: "2026-07-16T00:00:00Z",
              provider: "fixture",
              freshness_label: "fresh",
              data_mode: "fixture",
              execution_policy: "market_us_equity_simulated",
            },
            disclosure: "Simulated order only.",
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        );
      }),
    );

    const preview = await previewOrder(
      "p1",
      { symbol: "AAPL", side: "buy", quantity: "1" },
      { accessToken: "tok" },
    );
    expect(preview.preview_id).toBe("prev-1");
    expect(preview.quote.data_mode).toBe("fixture");
  });

  it("requires idempotency key on confirm", async () => {
    await expect(confirmOrder("p1", "prev-1", { accessToken: "tok" } as never)).rejects.toThrow(
      /Idempotency key/i,
    );
  });

  it("confirms with Idempotency-Key header", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (_url: string, init?: RequestInit) => {
        expect(init?.method).toBe("POST");
        const headers = init?.headers as Record<string, string>;
        expect(headers["Idempotency-Key"]).toBe("confirm-key-1");
        return new Response(
          JSON.stringify({
            receipt_id: "r1",
            order_id: "o1",
            request_id: "confirm-key-1",
            portfolio_id: "p1",
            status: "EXECUTED",
            symbol: "AAPL",
            side: "buy",
            quantity: "1.0000000000",
            notional: "190.0950",
            execution_price: "190.0950",
            fee: "0.0000",
            slippage_bps: "5.0000",
            ledger_entry_ids: ["l2"],
            position_quantity: "1.0000000000",
            position_delta: "1.0000000000",
            cash_balance: "809.9050",
            quote: {
              quote_id: "fixture:AAPL:x",
              quote_as_of: "2026-07-16T00:00:00Z",
              quote_received_at: "2026-07-16T00:00:00Z",
              provider: "fixture",
              freshness_label: "fresh",
              data_mode: "fixture",
              execution_policy: "market_us_equity_simulated",
            },
            simulated_at: "2026-07-16T00:00:01Z",
            disclosure: "Simulated order only.",
            created_at: "2026-07-16T00:00:01Z",
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        );
      }),
    );

    const receipt = await confirmOrder("p1", "prev-1", {
      accessToken: "tok",
      idempotencyKey: "confirm-key-1",
    });
    expect(receipt.status).toBe("EXECUTED");
    expect(receipt.cash_balance).toBe("809.9050");
  });
});
