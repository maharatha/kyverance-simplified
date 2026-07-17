import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ConnectedAccountsClient } from "./ConnectedAccountsClient";

const fetchConnectorsOverview = vi.fn();
const setPlaidConsent = vi.fn();
const fakeConnectPlaid = vi.fn();
const refreshConnection = vi.fn();
const disconnectConnection = vi.fn();
const requestConnectionDeletion = vi.fn();

vi.mock("next-auth/react", () => ({
  useSession: () => ({ data: { isDev: true, user: { name: "Dev User" } }, status: "authenticated" }),
}));

vi.mock("@/lib/connectors-api", () => ({
  fetchConnectorsOverview: (...args: unknown[]) => fetchConnectorsOverview(...args),
  setPlaidConsent: (...args: unknown[]) => setPlaidConsent(...args),
  fakeConnectPlaid: (...args: unknown[]) => fakeConnectPlaid(...args),
  refreshConnection: (...args: unknown[]) => refreshConnection(...args),
  disconnectConnection: (...args: unknown[]) => disconnectConnection(...args),
  requestConnectionDeletion: (...args: unknown[]) => requestConnectionDeletion(...args),
}));

vi.mock("next/link", () => ({
  default: ({ href, children, ...props }: { href: string; children: React.ReactNode }) => (
    <a href={href} {...props}>
      {children}
    </a>
  ),
}));

const emptyOverview = {
  configured: true,
  plaid_configured: false,
  mode: "fake",
  connect_consent_granted: false,
  data_retention_consent_granted: false,
  empty_state: "consent_required",
  connections: [],
  message: "Grant read-only connection consent before linking an account.",
};

const populatedOverview = {
  configured: true,
  plaid_configured: false,
  mode: "fake",
  connect_consent_granted: true,
  data_retention_consent_granted: true,
  empty_state: "populated",
  message: null,
  connections: [
    {
      id: "conn-1",
      provider_key: "any",
      institution_name: "Sample Bank (local fake)",
      status: "connected",
      last_synced_at: null,
      consent_recorded_at: null,
      disconnected_at: null,
      deletion_requested_at: null,
      accounts: [
        {
          id: "acct-1",
          connection_id: "conn-1",
          name: "Sample Brokerage",
          mask: "0000",
          account_type: "brokerage",
          currency: "USD",
          provenance: "plaid_read_only",
          source_label: "Linked account (read-only)",
          last_synced_at: null,
          holdings: [
            {
              id: "h-1",
              symbol: "VOO",
              name: "Vanguard S&P 500 ETF",
              quantity: "10.5",
              currency: "USD",
              provenance: "plaid_read_only",
              source_label: "Linked account (read-only)",
            },
          ],
        },
      ],
    },
  ],
};

describe("ConnectedAccountsClient", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows consent empty state and grants consent", async () => {
    fetchConnectorsOverview.mockResolvedValue(emptyOverview);
    setPlaidConsent.mockResolvedValue({
      ...emptyOverview,
      connect_consent_granted: true,
      empty_state: "ready_fake",
      message: "Local fake provider is active. No real banking credentials are used.",
    });

    render(<ConnectedAccountsClient />);

    expect(await screen.findByRole("heading", { name: "Connected Accounts" })).toBeInTheDocument();
    expect(screen.getByText(/explicit consent is required/i)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /grant read-only connect consent/i }));
    await waitFor(() => expect(setPlaidConsent).toHaveBeenCalledWith(true, expect.any(Object)));
    expect(await screen.findByText(/local fake provider is active/i)).toBeInTheDocument();
  });

  it("connects a sample account in fake mode and can disconnect", async () => {
    fetchConnectorsOverview.mockResolvedValue({
      ...emptyOverview,
      connect_consent_granted: true,
      empty_state: "ready_fake",
      message: "Local fake provider is active. No real banking credentials are used.",
    });
    fakeConnectPlaid.mockResolvedValue(populatedOverview);
    disconnectConnection.mockResolvedValue({
      ...populatedOverview,
      connections: [
        {
          ...populatedOverview.connections[0],
          status: "disconnected",
          accounts: [],
        },
      ],
    });

    render(<ConnectedAccountsClient />);

    expect(
      await screen.findByRole("button", { name: /connect sample read-only account/i }),
    ).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /connect sample read-only account/i }));

    expect(await screen.findByText("Sample Bank (local fake)")).toBeInTheDocument();
    expect(screen.getByText(/VOO/)).toBeInTheDocument();
    expect(screen.getByText(/Source: Linked account \(read-only\)/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Disconnect" }));
    await waitFor(() =>
      expect(disconnectConnection).toHaveBeenCalledWith("conn-1", expect.any(Object)),
    );
  });

  it("surfaces load errors", async () => {
    fetchConnectorsOverview.mockRejectedValue(new Error("Authentication required"));
    render(<ConnectedAccountsClient />);
    expect(await screen.findByRole("alert")).toHaveTextContent(/authentication required/i);
  });
});
