import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { SignInPanel } from "./SignInPanel";

const signIn = vi.fn();

vi.mock("next-auth/react", () => ({
  signIn: (...args: unknown[]) => signIn(...args),
}));

describe("SignInPanel", () => {
  it("offers Entra and local development actions when both are available", () => {
    render(<SignInPanel callbackUrl="/" entraReady localDev />);

    expect(screen.getByRole("button", { name: "Continue with Microsoft" })).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Continue as local developer" }),
    ).toBeInTheDocument();
  });

  it("explains missing Entra configuration without a live tenant", () => {
    render(<SignInPanel callbackUrl="/" entraReady={false} localDev />);

    expect(screen.getByRole("status")).toHaveTextContent(/not configured/i);
    fireEvent.click(screen.getByRole("button", { name: "Continue as local developer" }));
    expect(signIn).toHaveBeenCalledWith("development", { callbackUrl: "/" });
  });
});
