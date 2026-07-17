import { describe, expect, it } from "vitest";
import {
  formatMoney,
  formatSignedMoney,
  formatSignedPercent,
  provenanceLabel,
} from "./format";

describe("home format helpers", () => {
  it("formats supplied money strings without calculating totals", () => {
    expect(formatMoney("128450.27")).toBe("$128,450.27");
    expect(formatMoney("-12.5")).toBe("-$12.50");
  });

  it("formats signed money and percent with accessible sign text", () => {
    expect(formatSignedMoney("312.40")).toBe("+$312.40");
    expect(formatSignedPercent("0.24")).toBe("+0.24%");
    expect(formatSignedPercent("-1.2")).toBe("-1.2%");
  });

  it("maps provenance to readable labels", () => {
    expect(provenanceLabel("simulated")).toBe("Simulated");
    expect(provenanceLabel("manual_unverified")).toBe("Manual (unverified)");
    expect(provenanceLabel("connected_read_only")).toBe("Connected (read-only)");
  });
});
