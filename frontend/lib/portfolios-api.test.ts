import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import {
  createPortfolio,
  createPortfolioVersion,
  fetchPortfolio,
  fetchPortfolios,
  forkPortfolioVersion,
  publishPortfolioVersion,
} from "./portfolios-api";

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

  it("creates and publishes versions and forks", async () => {
    const fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
      if (String(url).includes("/versions") && init?.method === "POST" && !String(url).includes("publish")) {
        return new Response(
          JSON.stringify({
            id: "v1",
            portfolio_id: "p1",
            version_number: 1,
            name: "Core",
            description: null,
            thesis: null,
            agent_config_ref: null,
            holdings: [],
            allocation: {},
            data_context: {},
            checksum: "checksumvalue123",
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
          }),
          { status: 201, headers: { "Content-Type": "application/json" } },
        );
      }
      if (String(url).includes("/publish")) {
        return new Response(
          JSON.stringify({
            id: "v1",
            portfolio_id: "p1",
            version_number: 1,
            name: "Core",
            description: null,
            thesis: null,
            agent_config_ref: null,
            holdings: [],
            allocation: {},
            data_context: {},
            checksum: "checksumvalue123",
            status: "published",
            visibility: "public",
            provenance: "simulated",
            license: "public_fork_allowed",
            disclosure: "Simulated",
            consent_acknowledged: true,
            consent_text_version: "fork-01-v1",
            consent_at: "2026-07-17T00:00:00Z",
            published_at: "2026-07-17T00:00:00Z",
            created_at: "2026-07-17T00:00:00Z",
            fork_allowed: true,
            fork_notice: "independent",
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        );
      }
      if (String(url).includes("/fork")) {
        expect(init?.method).toBe("POST");
        return new Response(
          JSON.stringify({
            id: "p-fork",
            name: "My fork",
            description: null,
            visibility: "private",
            provenance: "simulated",
            status: "active",
            currency_code: "VUSD",
            cash_balance: "1000.0000",
            created_at: "2026-07-17T00:00:00Z",
            updated_at: "2026-07-17T00:00:00Z",
            fork_lineage: {
              id: "f1",
              source_portfolio_id: "p1",
              source_version_id: "v1",
              license: "public_fork_allowed",
              entitlement: "public_version_fork",
              sync_enabled: false,
              mirror_trades: false,
              forked_at: "2026-07-17T00:00:00Z",
            },
            wallet: {
              id: "w2",
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
      }
      return new Response("{}", { status: 404 });
    });
    vi.stubGlobal("fetch", fetchMock);

    const version = await createPortfolioVersion("p1", { idempotencyKey: "v-key" });
    expect(version.id).toBe("v1");
    const published = await publishPortfolioVersion("p1", "v1", {
      visibility: "public",
      license: "public_fork_allowed",
      consent_acknowledged: true,
    });
    expect(published.fork_allowed).toBe(true);
    const forked = await forkPortfolioVersion("v1", { name: "My fork" }, { idempotencyKey: "f-key" });
    expect(forked.fork_lineage?.sync_enabled).toBe(false);
  });
});
