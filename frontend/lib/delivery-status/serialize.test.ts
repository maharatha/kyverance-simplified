import { describe, expect, it } from "vitest";
import { isLocalDeliveryStatusEnabled } from "./guard";
import {
  assertNoAbsolutePaths,
  formatCursorSummary,
  formatDirtySummary,
  formatPreviewSummary,
  serializeDeliveryStatus,
  unavailableStatus,
} from "./serialize";

describe("delivery status guard", () => {
  it("enables collection only in development", () => {
    expect(isLocalDeliveryStatusEnabled("development")).toBe(true);
    expect(isLocalDeliveryStatusEnabled("production")).toBe(false);
    expect(isLocalDeliveryStatusEnabled("test")).toBe(false);
  });
});

describe("delivery status serialization", () => {
  it("serializes an available local board payload", () => {
    const status = serializeDeliveryStatus({
      checkedAt: "2026-07-17T16:00:00.000Z",
      branch: "codex/ops-01-local-delivery-board",
      commits: [
        {
          hash: "abc1234",
          subject: "Add local delivery board",
          when: "2 minutes ago",
        },
      ],
      dirtyFiles: ["frontend/app/delivery-status/page.tsx"],
      recentFiles: [
        {
          path: "docs/tasks/OPS-01-local-delivery-board.md",
          modifiedAt: "2026-07-17T15:59:00.000Z",
        },
      ],
      cursorProcessCount: 2,
      preview: {
        url: "http://127.0.0.1:3001/",
        healthy: true,
        statusCode: 200,
      },
    });

    expect(status.available).toBe(true);
    expect(status.branch).toBe("codex/ops-01-local-delivery-board");
    expect(status.cursorCli).toEqual({ active: true, processCount: 2 });
    expect(formatDirtySummary(status.dirtyFiles)).toBe("1 dirty file");
    expect(formatCursorSummary(status)).toBe(
      "2 Cursor Agent Node processes present (not proof of active editing)",
    );
    expect(formatPreviewSummary(status)).toBe("Healthy (HTTP 200)");
    expect(assertNoAbsolutePaths(status)).toEqual([]);
  });

  it("returns a clear unavailable payload outside local development", () => {
    const status = unavailableStatus("2026-07-17T16:00:00.000Z");
    expect(status.available).toBe(false);
    expect(status.reason).toMatch(/local Next\.js development/i);
    expect(formatCursorSummary(status)).toBe("Unavailable");
    expect(formatPreviewSummary(status)).toBe("Unavailable");
  });

  it("flags absolute filesystem paths if they leak into the payload", () => {
    const status = serializeDeliveryStatus({
      checkedAt: "2026-07-17T16:00:00.000Z",
      branch: "main",
      commits: [],
      dirtyFiles: ["C:\\SourceCode\\secret.ts"],
      recentFiles: [{ path: "/tmp/leak.ts", modifiedAt: "2026-07-17T16:00:00.000Z" }],
      cursorProcessCount: 0,
      preview: { url: "http://127.0.0.1:3001/", healthy: false, statusCode: null },
    });

    expect(assertNoAbsolutePaths(status).length).toBeGreaterThan(0);
    expect(formatCursorSummary(status)).toBe("No Cursor Agent Node processes present");
    expect(formatPreviewSummary(status)).toBe("Unavailable");
    expect(formatDirtySummary(status.dirtyFiles)).toBe("1 dirty file");
  });
});
