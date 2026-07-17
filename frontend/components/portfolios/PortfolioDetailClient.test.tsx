import { describe, expect, it, vi, beforeEach } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
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
const fetchPortfolioVersions = vi.fn();
const createPortfolioVersion = vi.fn();
const publishPortfolioVersion = vi.fn();
const patchPortfolio = vi.fn();

vi.mock("@/lib/portfolios-api", () => ({
  fetchPortfolio: (...args: unknown[]) => fetchPortfolio(...args),
  fetchPortfolioVersions: (...args: unknown[]) => fetchPortfolioVersions(...args),
  createPortfolioVersion: (...args: unknown[]) => createPortfolioVersion(...args),
  publishPortfolioVersion: (...args: unknown[]) => publishPortfolioVersion(...args),
  patchPortfolio: (...args: unknown[]) => patchPortfolio(...args),
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
      thesis: "Quality compounders",
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
      fork_lineage: null,
    });
    fetchPortfolioVersions.mockResolvedValue({ versions: [] });
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
    expect(screen.getByText(/Versions & publish/i)).toBeInTheDocument();
    expect(screen.getAllByText(/Quality compounders/i).length).toBeGreaterThan(0);
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("creates an immutable version from the publish panel", async () => {
    fetchPositions.mockResolvedValue({ positions: [] });
    fetchActivity.mockResolvedValue({ items: [] });
    createPortfolioVersion.mockResolvedValue({
      id: "v1",
      portfolio_id: "p1",
      version_number: 1,
      name: "Core Growth",
      description: null,
      thesis: "Quality compounders",
      agent_config_ref: null,
      holdings: [],
      allocation: {},
      data_context: {},
      checksum: "abc123checksumvalue",
      status: "draft",
      visibility: "private",
      provenance: "simulated",
      license: null,
      disclosure: null,
      consent_acknowledged: false,
      consent_text_version: null,
      consent_at: null,
      published_at: null,
      created_at: "2026-07-17T00:00:00Z",
      fork_allowed: false,
      fork_notice: null,
    });
    fetchPortfolioVersions
      .mockResolvedValueOnce({ versions: [] })
      .mockResolvedValue({
        versions: [
          {
            id: "v1",
            portfolio_id: "p1",
            version_number: 1,
            name: "Core Growth",
            description: null,
            thesis: "Quality compounders",
            agent_config_ref: null,
            holdings: [],
            allocation: {},
            data_context: {},
            checksum: "abc123checksumvalue",
            status: "draft",
            visibility: "private",
            provenance: "simulated",
            license: null,
            disclosure: null,
            consent_acknowledged: false,
            consent_text_version: null,
            consent_at: null,
            published_at: null,
            created_at: "2026-07-17T00:00:00Z",
            fork_allowed: false,
            fork_notice: null,
          },
        ],
      });

    render(<PortfolioDetailClient portfolioId="p1" />);

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /Create immutable version/i })).toBeInTheDocument();
    });
    fireEvent.click(screen.getByRole("button", { name: /Create immutable version/i }));
    await waitFor(() => {
      expect(createPortfolioVersion).toHaveBeenCalled();
      expect(screen.getByText(/v1 · draft/i)).toBeInTheDocument();
    });
  });
});
