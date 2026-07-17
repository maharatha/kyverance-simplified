import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { PortfoliosWorkspace } from "./PortfoliosWorkspace";

vi.mock("next-auth/react", () => ({
  useSession: () => ({
    data: { accessToken: "test-token" },
    status: "authenticated",
  }),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
}));

vi.mock("@/lib/portfolios-api", () => ({
  fetchPortfolios: vi.fn(async () => ({
    empty_state: "empty",
    portfolios: [],
  })),
  createPortfolio: vi.fn(),
  forkPortfolioVersion: vi.fn(),
}));

describe("PortfoliosWorkspace", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders empty state and create form", async () => {
    render(<PortfoliosWorkspace />);
    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Portfolios" })).toBeInTheDocument();
    });
    expect(
      screen.getByText(/No portfolios yet/i),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Create portfolio/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /Fork a public version/i })).toBeInTheDocument();
  });
});
