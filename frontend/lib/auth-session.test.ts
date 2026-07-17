import { describe, expect, it } from "vitest";
import { isSessionAuthenticated } from "@/lib/auth-session";
import { isLocalDevIdentityEnabled, PROTECTED_PREFIXES } from "@/auth.config";

describe("auth session helpers", () => {
  it("treats development and access-token sessions as authenticated", () => {
    expect(isSessionAuthenticated({ isDev: true, user: { id: "dev-user-001" } })).toBe(true);
    expect(
      isSessionAuthenticated({
        accessToken: "token",
        user: { id: "oid" },
      }),
    ).toBe(true);
    expect(isSessionAuthenticated({ error: "RefreshAccessTokenError", user: { id: "x" } })).toBe(
      false,
    );
    expect(isSessionAuthenticated(null)).toBe(false);
  });

  it("keeps protected prefixes focused on the application shell", () => {
    expect(PROTECTED_PREFIXES).toContain("/profile");
  });

  it("disables local development identity in production", () => {
    const previous = process.env.NODE_ENV;
    const previousFlag = process.env.AUTH_DEV_IDENTITY;
    process.env.NODE_ENV = "production";
    process.env.AUTH_DEV_IDENTITY = "true";
    expect(isLocalDevIdentityEnabled()).toBe(false);
    process.env.NODE_ENV = previous;
    process.env.AUTH_DEV_IDENTITY = previousFlag;
  });
});
