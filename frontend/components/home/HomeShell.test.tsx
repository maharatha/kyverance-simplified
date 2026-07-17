import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { getHomeFixture, HOME_PAGE_STATES } from "@/lib/home";
import { HomeShell } from "./HomeShell";
import "./home.css";

describe("HomeShell states", () => {
  it("covers every documented home state with fixtures", () => {
    expect(HOME_PAGE_STATES).toEqual([
      "signed-out",
      "new-member",
      "active-member",
      "creator",
      "agent-proposal",
      "loading",
      "unavailable",
    ]);
  });

  it("renders signed-out with simulation disclosure and one primary CTA", () => {
    render(<HomeShell fixture={getHomeFixture("signed-out")} sessionSignedIn={false} />);

    expect(
      screen.getByRole("heading", {
        level: 1,
        name: "Build an investing process you can inspect.",
      }),
    ).toBeInTheDocument();

    const primary = screen.getByRole("link", { name: "Create a simulated portfolio" });
    expect(primary).toHaveClass("btn-primary");
    expect(screen.getByRole("link", { name: "Explore portfolios" })).toHaveClass("btn-ghost");
    expect(screen.getByRole("status")).toHaveTextContent(/Simulation only/i);
    expect(screen.getByRole("navigation", { name: "Primary" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Sign in" })).toBeInTheDocument();
  });

  it("prefers real session state over fixture for the header", () => {
    render(<HomeShell fixture={getHomeFixture("signed-out")} sessionSignedIn />);
    expect(screen.getByRole("link", { name: "Profile" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Sign in" })).not.toBeInTheDocument();
  });

  it("renders new-member starter path with a single primary CTA", () => {
    render(<HomeShell fixture={getHomeFixture("new-member")} />);

    expect(screen.getByRole("heading", { name: "Start with one portfolio." })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Create portfolio" })).toHaveClass("btn-primary");
    expect(screen.getByRole("heading", { name: "Starter path" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /1\. Define an objective/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /2\. Add or watch an asset/i })).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: /3\. Review a simulated decision/i }),
    ).toBeInTheDocument();
  });

  it("renders active-member facts before agent content and keeps one primary CTA", () => {
    const { container } = render(<HomeShell fixture={getHomeFixture("active-member")} />);

    expect(screen.getByRole("heading", { name: "Your next best review." })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Review agent brief" })).toHaveClass("btn-primary");

    const portfolio = screen.getByRole("heading", { name: "Core Growth Practice" });
    const agent = screen.getByRole("heading", { name: "Agent brief" });
    expect(
      portfolio.compareDocumentPosition(agent) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();

    expect(screen.getByText("Simulated")).toBeInTheDocument();
    expect(screen.getAllByText(/As of/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/\$128,450\.27/)).toBeInTheDocument();
    expect(screen.getByText(/Up \+0\.24%/)).toBeInTheDocument();
    expect(container.querySelectorAll(".btn-primary")).toHaveLength(1);
  });

  it("renders creator draft status and community signal", () => {
    render(<HomeShell fixture={getHomeFixture("creator")} />);

    expect(
      screen.getByRole("heading", { name: "Publish the work behind the performance." }),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Publish a version" })).toHaveClass("btn-primary");
    expect(screen.getByText("Draft")).toBeInTheDocument();
    expect(screen.getByText(/v0\.9 draft/i)).toBeInTheDocument();
    expect(screen.getByText(/12 watchers/i)).toBeInTheDocument();
  });

  it("labels agent proposals as draft with no trade placed", () => {
    render(<HomeShell fixture={getHomeFixture("agent-proposal")} />);

    expect(
      screen.getByRole("heading", { name: "An agent prepared a scenario for review." }),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Review proposal" })).toHaveClass("btn-primary");
    expect(screen.getByText(/Scenario \/ draft — no trade placed/i)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Assumptions" })).toBeInTheDocument();
    expect(screen.getByText(/6 evidence items/i)).toBeInTheDocument();
  });

  it("preserves loading skeletons without presenting stale portfolio values", () => {
    render(<HomeShell fixture={getHomeFixture("loading")} />);

    expect(screen.getByText(/Loading portfolio and agent context/i)).toBeInTheDocument();
    expect(screen.queryByText(/\$128,450\.27/)).not.toBeInTheDocument();
    expect(document.querySelectorAll(".home-skeleton-block").length).toBeGreaterThan(0);
  });

  it("hides stale values in unavailable state and offers recovery", () => {
    render(<HomeShell fixture={getHomeFixture("unavailable")} />);

    expect(screen.getByRole("alert")).toHaveTextContent(/unavailable|withheld/i);
    expect(screen.queryByText(/\$128,450\.27/)).not.toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: "Retry home" }).length).toBeGreaterThan(0);
    expect(screen.getByText(/Agent brief unavailable/i)).toBeInTheDocument();
  });

  it("exposes allocation table as an accessible alternate", () => {
    render(<HomeShell fixture={getHomeFixture("active-member")} />);

    fireEvent.click(screen.getByRole("button", { name: "View allocation as table" }));
    const table = screen.getByRole("table", { name: /Portfolio allocation percentages/i });
    expect(within(table).getByText("Equities")).toBeInTheDocument();
    expect(within(table).getByText("62.0%")).toBeInTheDocument();
  });

  it("keeps landmark and keyboard-focusable primary controls", () => {
    render(<HomeShell fixture={getHomeFixture("active-member")} />);

    expect(screen.getByRole("banner")).toBeInTheDocument();
    expect(screen.getByRole("main")).toBeInTheDocument();
    const primary = screen.getByRole("link", { name: "Review agent brief" });
    primary.focus();
    expect(primary).toHaveFocus();
  });
});
