import { describe, expect, it } from "vitest";
import { collectDeliveryStatus } from "./collect";

describe("collectDeliveryStatus", () => {
  it("does not collect workspace telemetry outside development", async () => {
    const status = await collectDeliveryStatus({ nodeEnv: "production" });
    expect(status.available).toBe(false);
    if (!status.available) {
      expect(status.reason).toMatch(/local Next\.js development/i);
    }
  });
});
