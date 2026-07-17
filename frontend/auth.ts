import NextAuth from "next-auth";
import Credentials from "next-auth/providers/credentials";
import MicrosoftEntraID from "next-auth/providers/microsoft-entra-id";
import { authConfig } from "./auth.config";
import {
  apiScope,
  authEnv,
  entraProviderConfig,
  isEntraConfigured,
  isLocalDevIdentityEnabled,
  resolveAuthSecret,
  tokenUrl,
} from "./lib/auth-env";

function decodeJwtPayload(token: string): Record<string, unknown> {
  const part = token.split(".")[1];
  if (!part) return {};
  try {
    const json = Buffer.from(part, "base64url").toString("utf8");
    return JSON.parse(json) as Record<string, unknown>;
  } catch {
    return {};
  }
}

function isSyntheticEmail(value?: string): boolean {
  if (!value) return true;
  const email = value.trim().toLowerCase();
  if (!email.includes("@")) return true;
  if (email.endsWith("@onmicrosoft.com")) return true;
  if (/^[0-9a-f-]{36}@.*\.onmicrosoft\.com$/i.test(email)) return true;
  return false;
}

function pickRealEmail(...candidates: (string | undefined)[]): string | undefined {
  for (const candidate of candidates) {
    if (candidate && !isSyntheticEmail(candidate)) return candidate.trim();
  }
  return undefined;
}

function sanitizeName(value?: string): string | undefined {
  if (!value) return undefined;
  const trimmed = value.trim();
  if (!trimmed) return undefined;
  const lower = trimmed.toLowerCase();
  if (lower === "unknown" || lower === "n/a" || lower === "anonymous") return undefined;
  return trimmed;
}

function tokenExpiresAtMs(accessToken: string): number | null {
  const exp = decodeJwtPayload(accessToken).exp;
  return typeof exp === "number" ? exp * 1000 : null;
}

function claimString(claims: Record<string, unknown>, key: string): string | undefined {
  const value = claims[key];
  return typeof value === "string" && value ? value : undefined;
}

function applyIdentityClaims(
  token: Record<string, unknown>,
  claims: Record<string, unknown>,
): void {
  const oid = claimString(claims, "oid");
  const sub = claimString(claims, "sub");
  if (oid) token.sub = oid;
  else if (sub) token.sub = sub;

  const name =
    sanitizeName(claimString(claims, "name")) ??
    sanitizeName(
      `${claimString(claims, "given_name") ?? ""} ${claimString(claims, "family_name") ?? ""}`.trim(),
    );
  if (name) token.name = name;

  const realEmail = pickRealEmail(
    claimString(claims, "email"),
    claimString(claims, "preferred_username"),
    claimString(claims, "upn"),
  );
  if (realEmail) token.email = realEmail;
}

const REFRESH_BUFFER_MS = 5 * 60 * 1000;

async function refreshAccessToken(token: Record<string, unknown>): Promise<Record<string, unknown>> {
  const refreshToken = token.refreshToken as string | undefined;
  if (!refreshToken || !tokenUrl) {
    return { ...token, error: "RefreshTokenMissing" };
  }

  const clientId = authEnv("AUTH_ENTRA_CLIENT_ID", "AUTH_MICROSOFT_ENTRA_ID_ID");
  const clientSecret = authEnv("AUTH_ENTRA_CLIENT_SECRET", "AUTH_MICROSOFT_ENTRA_ID_SECRET");
  if (!clientId || !clientSecret) {
    return { ...token, error: "RefreshTokenMissing" };
  }

  try {
    const response = await fetch(tokenUrl, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({
        client_id: clientId,
        client_secret: clientSecret,
        grant_type: "refresh_token",
        refresh_token: refreshToken,
        scope: `openid profile email offline_access ${apiScope}`,
      }),
    });
    const data = (await response.json()) as {
      access_token?: string;
      id_token?: string;
      refresh_token?: string;
      expires_in?: number;
      expires_at?: number;
      error?: string;
      error_description?: string;
    };

    if (!response.ok || !data.access_token) {
      throw new Error(data.error_description || data.error || "Token refresh failed");
    }

    const expiresAtMs = tokenExpiresAtMs(data.access_token);
    const expiresAt =
      data.expires_at ??
      (expiresAtMs
        ? Math.floor(expiresAtMs / 1000)
        : Math.floor(Date.now() / 1000) + (data.expires_in ?? 3600));

    const next: Record<string, unknown> = {
      ...token,
      accessToken: data.access_token,
      refreshToken: data.refresh_token ?? refreshToken,
      expiresAt,
      error: undefined,
    };
    if (data.id_token) {
      next.idToken = data.id_token;
      applyIdentityClaims(next, decodeJwtPayload(data.id_token));
    }
    applyIdentityClaims(next, decodeJwtPayload(data.access_token));
    return next;
  } catch {
    return { ...token, error: "RefreshAccessTokenError" };
  }
}

const providers = [];

if (isEntraConfigured() && entraProviderConfig.issuer) {
  providers.push(
    MicrosoftEntraID({
      clientId: entraProviderConfig.clientId!,
      clientSecret: entraProviderConfig.clientSecret!,
      issuer: entraProviderConfig.issuer,
      authorization: entraProviderConfig.authorizeUrl
        ? {
            url: entraProviderConfig.authorizeUrl,
            params: {
              scope: `openid profile email offline_access ${entraProviderConfig.apiScope}`,
              ...(entraProviderConfig.userFlow ? { p: entraProviderConfig.userFlow } : {}),
            },
          }
        : {
            params: {
              scope: `openid profile email offline_access ${entraProviderConfig.apiScope}`,
            },
          },
      ...(entraProviderConfig.tokenUrl ? { token: entraProviderConfig.tokenUrl } : {}),
    }),
  );
}

if (isLocalDevIdentityEnabled()) {
  providers.push(
    Credentials({
      id: "development",
      name: "Local development",
      credentials: {
        confirm: { label: "Confirm", type: "text" },
      },
      async authorize() {
        if (!isLocalDevIdentityEnabled()) return null;
        return {
          id: "dev-user-001",
          name: "Dev User",
          email: "dev@kyverance.local",
          isDev: true,
        };
      },
    }),
  );
}

export const { handlers, auth, signIn, signOut } = NextAuth({
  ...authConfig,
  secret: resolveAuthSecret(),
  providers,
  callbacks: {
    ...authConfig.callbacks,
    async jwt({ token, account, profile, user }) {
      if (user && (user as { isDev?: boolean }).isDev) {
        token.sub = user.id ?? "dev-user-001";
        token.name = user.name ?? "Dev User";
        token.email = user.email ?? "dev@kyverance.local";
        token.isDev = true;
        token.error = undefined;
        return token;
      }

      if (account) {
        if (account.access_token) token.accessToken = account.access_token;
        if (account.id_token) {
          token.idToken = account.id_token;
          applyIdentityClaims(token, decodeJwtPayload(account.id_token));
          const idClaims = decodeJwtPayload(account.id_token);
          const idp = claimString(idClaims, "idp") ?? claimString(idClaims, "identityProvider");
          if (idp) token.idp = idp;
        }
        if (account.refresh_token) token.refreshToken = account.refresh_token;
        if (account.access_token) applyIdentityClaims(token, decodeJwtPayload(account.access_token));
        const expiresAtMs = account.access_token ? tokenExpiresAtMs(account.access_token) : null;
        token.expiresAt =
          account.expires_at ??
          (expiresAtMs
            ? Math.floor(expiresAtMs / 1000)
            : Math.floor(Date.now() / 1000) + (account.expires_in ?? 3600));
        token.error = undefined;
        token.isDev = false;
        return token;
      }

      if (profile) {
        applyIdentityClaims(token, profile as Record<string, unknown>);
      }

      if (token.isDev) {
        return token;
      }

      const expiresAt = token.expiresAt as number | undefined;
      if (expiresAt && Date.now() < expiresAt * 1000 - REFRESH_BUFFER_MS) {
        return token;
      }

      if (token.refreshToken) {
        return refreshAccessToken(token as Record<string, unknown>);
      }

      return token;
    },
    session({ session, token }) {
      if (
        token.error === "RefreshAccessTokenError" ||
        token.error === "RefreshTokenMissing" ||
        token.error === "SignedOut"
      ) {
        session.error = token.error as string;
        session.user.name = "";
        session.user.email = "";
        session.user.image = "";
        delete session.accessToken;
        delete session.idToken;
        delete session.idp;
        delete session.isDev;
        return session;
      }

      if (token.isDev) {
        session.isDev = true;
        if (token.sub) session.user.id = token.sub as string;
        if (token.name) session.user.name = sanitizeName(token.name as string);
        if (token.email) session.user.email = token.email as string;
        return session;
      }

      if (!token.accessToken) {
        session.user.name = "";
        session.user.email = "";
        session.user.image = "";
        return session;
      }

      session.accessToken = token.accessToken as string;
      if (token.idToken) session.idToken = token.idToken as string;
      if (token.sub) session.user.id = token.sub as string;
      if (token.name) session.user.name = sanitizeName(token.name as string);
      if (token.email) session.user.email = token.email as string;
      if (token.idp) session.idp = token.idp as string;
      return session;
    },
  },
});

declare module "next-auth" {
  interface Session {
    accessToken?: string;
    idToken?: string;
    idp?: string;
    isDev?: boolean;
    error?: string;
  }

  interface User {
    isDev?: boolean;
  }
}

declare module "@auth/core/jwt" {
  interface JWT {
    accessToken?: string;
    idToken?: string;
    idp?: string;
    refreshToken?: string;
    expiresAt?: number;
    isDev?: boolean;
    error?: string;
  }
}
