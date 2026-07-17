/**
 * Helpers for Entra External ID / Auth.js sign-in (no live tenant values).
 */

export function signInAuthorizationParams(): Record<string, string> {
  const apiScope =
    process.env.AUTH_ENTRA_API_SCOPE ?? "api://kyverance-api/access_as_user";
  return {
    scope: `openid profile email offline_access ${apiScope}`,
    prompt: "login",
  };
}

export function isSessionAuthenticated(session: {
  user?: { id?: string | null; name?: string | null } | null;
  accessToken?: string;
  isDev?: boolean;
  error?: string;
} | null): boolean {
  if (!session || session.error) return false;
  if (session.isDev) return true;
  if (session.accessToken) return true;
  return Boolean(session.user?.id);
}
