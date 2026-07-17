import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("next-auth/react", () => ({
  useSession: () => ({ data: null, status: "unauthenticated" }),
  signOut: vi.fn(),
  SessionProvider: ({ children }: { children: React.ReactNode }) => children,
}));

import { HomePageClient } from "./HomePageClient";

describe("HomePageClient", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("does not expose the state switcher in production builds", () => {
    vi.stubEnv("NODE_ENV", "production");
    render(<HomePageClient initialState="active-member" />);

    expect(screen.queryByLabelText("Dev home state")).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Delivery board" })).not.toBeInTheDocument();
    expect(
      screen.getByRole("heading", {
        name: "Build an investing process you can inspect.",
      }),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Sign in" })).toBeInTheDocument();
  });

  it("links to the local delivery board from the developer header", () => {
    vi.stubEnv("NODE_ENV", "development");
    render(<HomePageClient initialState="signed-out" />);

    expect(screen.getByLabelText("Dev home state")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Delivery board" })).toHaveAttribute(
      "href",
      "/delivery-status",
    );
  });

  it("allows fixture state selection outside production", () => {
    vi.stubEnv("NODE_ENV", "test");
    render(<HomePageClient initialState="creator" />);

    expect(
      screen.getByRole("heading", {
        name: "Publish the work behind the performance.",
      }),
    ).toBeInTheDocument();
  });

  it("renders Profile from real session even when fixture is signed-out", () => {
    vi.stubEnv("NODE_ENV", "test");
    render(<HomePageClient initialState="signed-out" sessionSignedIn />);

    expect(screen.getByRole("link", { name: "Profile" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Sign in" })).not.toBeInTheDocument();
  });
});
