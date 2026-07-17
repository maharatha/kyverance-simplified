import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  disconnectConnection,
  exchangePlaidToken,
  fakeConnectPlaid,
  fetchConnectorsOverview,
} from "./connectors-api";

describe("connectors-api", () => {
  beforeEach(() => {
    vi.unstubAllGlobals();
  });

  it("builds connector URLs against the public API base", async () => {
    const calls: Array<{ url: string; init?: RequestInit }> = [];
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string, init?: RequestInit) => {
        calls.push({ url, init });
        return {
          ok: true,
          json: async () => ({
            configured: true,
            plaid_configured: false,
            mode: "fake",
            connect_consent_granted: true,
            data_retention_consent_granted: true,
            empty_state: "ready_fake",
            connections: [],
            message: null,
          }),
        };
      }),
    );

    await fetchConnectorsOverview();
    await exchangePlaidToken("public-fake-demo");
    await fakeConnectPlaid();
    await disconnectConnection("abc");

    expect(calls[0].url).toContain("/api/v1/connectors");
    expect(calls[1].url).toContain("/api/v1/connectors/plaid/exchange");
    expect(calls[1].init?.method).toBe("POST");
    expect(calls[2].url).toContain("/api/v1/connectors/plaid/fake-connect");
    expect(calls[3].url).toContain("/api/v1/connectors/connections/abc");
    expect(calls[3].init?.method).toBe("DELETE");
  });
});
