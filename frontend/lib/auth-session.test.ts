import { describe, expect, it } from "vitest";
import {
  LOCAL_DEV_AUTH_SECRET,
  isLocalDevIdentityEnabled,
  resolveAuthSecret,
} from "@/lib/auth-env";
import { hasSessionCookie, isProtectedPath, PROTECTED_PREFIXES } from "@/lib/auth-routes";
import { isSessionAuthenticated } from "@/lib/auth-session";

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
    expect(isProtectedPath("/profile")).toBe(true);
    expect(isProtectedPath("/")).toBe(false);
    expect(isProtectedPath("/sign-in")).toBe(false);
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

describe("auth secret resolution", () => {
  it("uses a local-only fallback when AUTH_SECRET is unset outside production", () => {
    const previousEnv = process.env.NODE_ENV;
    const previousSecret = process.env.AUTH_SECRET;
    const previousNextAuth = process.env.NEXTAUTH_SECRET;
    process.env.NODE_ENV = "development";
    delete process.env.AUTH_SECRET;
    delete process.env.NEXTAUTH_SECRET;
    expect(resolveAuthSecret()).toBe(LOCAL_DEV_AUTH_SECRET);
    process.env.NODE_ENV = previousEnv;
    if (previousSecret === undefined) delete process.env.AUTH_SECRET;
    else process.env.AUTH_SECRET = previousSecret;
    if (previousNextAuth === undefined) delete process.env.NEXTAUTH_SECRET;
    else process.env.NEXTAUTH_SECRET = previousNextAuth;
  });

  it("fails closed in production when AUTH_SECRET is unset", () => {
    const previousEnv = process.env.NODE_ENV;
    const previousSecret = process.env.AUTH_SECRET;
    const previousNextAuth = process.env.NEXTAUTH_SECRET;
    process.env.NODE_ENV = "production";
    delete process.env.AUTH_SECRET;
    delete process.env.NEXTAUTH_SECRET;
    expect(resolveAuthSecret()).toBeUndefined();
    process.env.NODE_ENV = previousEnv;
    if (previousSecret === undefined) delete process.env.AUTH_SECRET;
    else process.env.AUTH_SECRET = previousSecret;
    if (previousNextAuth === undefined) delete process.env.NEXTAUTH_SECRET;
    else process.env.NEXTAUTH_SECRET = previousNextAuth;
  });

  it("prefers an explicit AUTH_SECRET over the local fallback", () => {
    const previousSecret = process.env.AUTH_SECRET;
    process.env.AUTH_SECRET = "explicit-local-secret";
    expect(resolveAuthSecret()).toBe("explicit-local-secret");
    if (previousSecret === undefined) delete process.env.AUTH_SECRET;
    else process.env.AUTH_SECRET = previousSecret;
  });
});

describe("edge route gating helpers", () => {
  it("detects Auth.js session cookies without importing next-auth", () => {
    expect(hasSessionCookie(["authjs.session-token"])).toBe(true);
    expect(hasSessionCookie(["__Secure-authjs.session-token"])).toBe(true);
    expect(hasSessionCookie(["unrelated"])).toBe(false);
  });
});
