import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { DeliveryStatusBoard } from "./DeliveryStatusBoard";
import type { DeliveryStatus } from "@/lib/delivery-status/types";

const availableStatus: DeliveryStatus = {
  available: true,
  checkedAt: "2026-07-17T16:00:00.000Z",
  branch: "codex/ops-01-local-delivery-board",
  commits: [
    {
      hash: "abc1234",
      subject: "Add local delivery board",
      when: "2 minutes ago",
    },
  ],
  dirtyFiles: ["frontend/lib/delivery-status/serialize.ts"],
  recentFiles: [
    {
      path: "docs/tasks/OPS-01-local-delivery-board.md",
      modifiedAt: "2026-07-17T15:59:00.000Z",
    },
  ],
  cursorCli: { active: true, processCount: 1 },
  preview: {
    url: "http://127.0.0.1:3001/",
    healthy: true,
    statusCode: 200,
  },
};

const unavailableStatus: DeliveryStatus = {
  available: false,
  checkedAt: "2026-07-17T16:00:00.000Z",
  reason: "Delivery status is available only during local Next.js development (`next dev`).",
};

describe("DeliveryStatusBoard", () => {
  it("renders local board fields from serialized status", () => {
    render(<DeliveryStatusBoard initialStatus={availableStatus} autoRefresh={false} />);

    expect(
      screen.getByRole("heading", { name: "Local delivery board" }),
    ).toBeInTheDocument();
    expect(screen.getByText("codex/ops-01-local-delivery-board")).toBeInTheDocument();
    expect(
      screen.getByText("1 Cursor Agent Node process present (not proof of active editing)"),
    ).toBeInTheDocument();
    expect(screen.getByText("http://127.0.0.1:3001/")).toBeInTheDocument();
    expect(screen.getByText("Healthy (HTTP 200)")).toBeInTheDocument();
    expect(screen.getByText("1 dirty file")).toBeInTheDocument();
    expect(screen.getByText("Add local delivery board")).toBeInTheDocument();
    expect(
      screen.getByText("docs/tasks/OPS-01-local-delivery-board.md"),
    ).toBeInTheDocument();
  });

  it("renders a clear unavailable state outside local development", () => {
    render(<DeliveryStatusBoard initialStatus={unavailableStatus} autoRefresh={false} />);

    expect(screen.getByText("Unavailable outside local development.")).toBeInTheDocument();
    expect(
      screen.getByText(/available only during local Next\.js development/i),
    ).toBeInTheDocument();
  });
});
