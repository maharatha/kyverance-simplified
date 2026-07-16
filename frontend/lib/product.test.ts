import { describe, expect, it } from "vitest";
import { PRODUCT_NAME, PRODUCT_TAGLINE } from "./product";

describe("product constants", () => {
  it("exposes the brand name", () => {
    expect(PRODUCT_NAME).toBe("Kyverance");
  });

  it("exposes a short tagline", () => {
    expect(PRODUCT_TAGLINE.length).toBeGreaterThan(10);
  });
});
