import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { HomePageClient } from "./HomePageClient";

describe("HomePageClient", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("does not expose the state switcher in production builds", () => {
    vi.stubEnv("NODE_ENV", "production");
    render(<HomePageClient initialState="active-member" />);

    expect(screen.queryByLabelText("Dev home state")).not.toBeInTheDocument();
    expect(
      screen.getByRole("heading", {
        name: "Build an investing process you can inspect.",
      }),
    ).toBeInTheDocument();
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
});
