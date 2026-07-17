import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { PortfolioDetailClient } from "./PortfolioDetailClient";

vi.mock("next/link", () => ({
  default: ({ children, href }: { children: ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
}));

vi.mock("next-auth/react", () => ({
  useSession: () => ({
    data: { accessToken: "test-token" },
    status: "authenticated",
  }),
}));

const fetchPortfolio = vi.fn();
const fetchPositions = vi.fn();
const fetchActivity = vi.fn();

vi.mock("@/lib/portfolios-api", () => ({
  fetchPortfolio: (...args: unknown[]) => fetchPortfolio(...args),
}));

vi.mock("@/lib/orders-api", () => ({
  fetchPositions: (...args: unknown[]) => fetchPositions(...args),
  fetchActivity: (...args: unknown[]) => fetchActivity(...args),
  previewOrder: vi.fn(),
  confirmOrder: vi.fn(),
}));

describe("PortfolioDetailClient", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    fetchPortfolio.mockResolvedValue({
      id: "p1",
      name: "Core Growth",
      description: "Sim book",
      visibility: "private",
      provenance: "simulated",
      status: "active",
      simulation_notice: "Simulated only",
      wallet: {
        id: "w1",
        cash_balance: "1000.0000",
        complimentary_balance: "1000.0000",
        currency_code: "VUSD",
        version: 1,
      },
      ledger: [],
    });
  });

  it("still renders portfolio when positions/activity endpoints fail", async () => {
    fetchPositions.mockRejectedValue(new Error("Not Found"));
    fetchActivity.mockRejectedValue(new Error("Not Found"));

    render(<PortfolioDetailClient portfolioId="p1" />);

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Core Growth" })).toBeInTheDocument();
    });
    expect(screen.getByText(/Virtual wallet/i)).toBeInTheDocument();
    expect(screen.getByText(/Simulated market order/i)).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });
});
