import { describe, expect, it, vi, beforeEach } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { OrderLoopPanel } from "./OrderLoopPanel";

vi.mock("@/lib/orders-api", () => ({
  previewOrder: vi.fn(async () => ({
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
    disclosure: "Simulated order only. No real trade is sent to a broker or exchange.",
  })),
  confirmOrder: vi.fn(async () => ({
    receipt_id: "r1",
    order_id: "o1",
    request_id: "k1",
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
  })),
}));

describe("OrderLoopPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("requires explicit confirm after preview", async () => {
    const onMutated = vi.fn(async () => undefined);
    render(
      <OrderLoopPanel
        portfolioId="p1"
        currencyCode="VUSD"
        accessToken="tok"
        positions={[]}
        activity={[]}
        onMutated={onMutated}
      />,
    );

    expect(screen.getByRole("button", { name: /Preview order/i })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Confirm simulated order/i })).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Preview order/i }));
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /Confirm simulated order/i })).toBeInTheDocument();
    });
    expect(screen.getByText(/Data mode: fixture/i)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Confirm simulated order/i }));
    await waitFor(() => {
      expect(screen.getByText(/Receipt EXECUTED/i)).toBeInTheDocument();
    });
    expect(onMutated).toHaveBeenCalled();
  });
});
