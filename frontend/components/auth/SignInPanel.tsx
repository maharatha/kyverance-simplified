"use client";

import { signIn } from "next-auth/react";
import { useState } from "react";
import { signInAuthorizationParams } from "@/lib/auth-session";

type SignInPanelProps = {
  callbackUrl: string;
  entraReady: boolean;
  localDev: boolean;
};

export function SignInPanel({ callbackUrl, entraReady, localDev }: SignInPanelProps) {
  const [pending, setPending] = useState<"entra" | "dev" | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function startEntra() {
    setError(null);
    setPending("entra");
    try {
      await signIn("microsoft-entra-id", { callbackUrl }, signInAuthorizationParams());
    } catch {
      setError("Sign-in could not start. Check Entra configuration and try again.");
      setPending(null);
    }
  }

  async function startLocalDev() {
    setError(null);
    setPending("dev");
    try {
      await signIn("development", { callbackUrl });
    } catch {
      setError("Local development identity is unavailable.");
      setPending(null);
    }
  }

  return (
    <div className="sign-in-actions">
      {entraReady ? (
        <button
          type="button"
          className="btn-primary"
          disabled={pending !== null}
          onClick={() => void startEntra()}
        >
          {pending === "entra" ? "Redirecting…" : "Continue with Microsoft"}
        </button>
      ) : (
        <p className="sign-in-note" role="status">
          Microsoft Entra sign-in is not configured in this environment. Set the
          documented AUTH_ENTRA_* variables after app registration provisioning.
        </p>
      )}

      {localDev ? (
        <button
          type="button"
          className="btn-secondary"
          disabled={pending !== null}
          onClick={() => void startLocalDev()}
        >
          {pending === "dev" ? "Signing in…" : "Continue as local developer"}
        </button>
      ) : null}

      {error ? (
        <p className="sign-in-error" role="alert">
          {error}
        </p>
      ) : null}
    </div>
  );
}
