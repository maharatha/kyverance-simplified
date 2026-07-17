import { describe, expect, it } from "vitest";
import { NextRequest } from "next/server";
import { middleware } from "@/middleware";

function requestFor(path: string, cookieHeader?: string) {
  const headers = new Headers();
  if (cookieHeader) headers.set("cookie", cookieHeader);
  return new NextRequest(new URL(path, "http://localhost:3000"), { headers });
}

describe("edge middleware route gate", () => {
  it("allows public home and sign-in without a session cookie", async () => {
    const home = middleware(requestFor("/"));
    const signIn = middleware(requestFor("/sign-in"));
    expect(home.status).toBe(200);
    expect(signIn.status).toBe(200);
  });

  it("redirects protected routes to sign-in when unsigned", async () => {
    const response = middleware(requestFor("/profile"));
    expect(response.status).toBe(307);
    expect(response.headers.get("location")).toContain("/sign-in?callbackUrl=%2Fprofile");
  });

  it("allows protected routes when an Auth.js session cookie is present", async () => {
    const response = middleware(
      requestFor("/profile", "authjs.session-token=test-session-value"),
    );
    expect(response.status).toBe(200);
  });
});
