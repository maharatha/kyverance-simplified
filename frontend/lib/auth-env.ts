/**
 * Auth environment helpers (Edge-safe: no Node Buffer / Jose / fetch refresh).
 */

function env(...keys: string[]): string | undefined {
  for (const key of keys) {
    const value = process.env[key];
    if (value && value.trim()) return value.trim();
  }
  return undefined;
}

const tenantId = env("AUTH_ENTRA_TENANT_ID") ?? "";
const userFlow = env("AUTH_ENTRA_USER_FLOW") ?? "SignUpSignIn";
const ciamHost = env("AUTH_ENTRA_CIAM_DOMAIN") ?? "";
const apiScope =
  env("AUTH_ENTRA_API_SCOPE") ?? "api://kyverance-api/access_as_user";
const issuer =
  env("AUTH_ENTRA_ISSUER", "AUTH_MICROSOFT_ENTRA_ID_ISSUER") ??
  (tenantId ? `https://${tenantId}.ciamlogin.com/${tenantId}/v2.0` : "");

const authorizeUrl =
  tenantId && ciamHost
    ? `https://${ciamHost}/${tenantId}/oauth2/v2.0/authorize`
    : undefined;
const tokenUrl =
  tenantId && ciamHost
    ? `https://${ciamHost}/${tenantId}/oauth2/v2.0/token`
    : undefined;

/** Well-known local-only cookie encryption secret — never used when NODE_ENV=production. */
export const LOCAL_DEV_AUTH_SECRET = "kyverance-local-dev-only-auth-secret";

/**
 * Resolve Auth.js secret. Production requires AUTH_SECRET / NEXTAUTH_SECRET (fail-closed).
 * Non-production may use a deterministic local fallback so public pages work without .env.
 */
export function resolveAuthSecret(): string | undefined {
  const configured = env("AUTH_SECRET", "NEXTAUTH_SECRET");
  if (configured) return configured;
  if (process.env.NODE_ENV !== "production") return LOCAL_DEV_AUTH_SECRET;
  return undefined;
}

export function isLocalDevIdentityEnabled(): boolean {
  if (process.env.NODE_ENV === "production") return false;
  const flag = (process.env.AUTH_DEV_IDENTITY ?? process.env.NEXT_PUBLIC_DEV_AUTH ?? "").toLowerCase();
  return flag === "true" || flag === "1";
}

export function isEntraConfigured(): boolean {
  const clientId = env("AUTH_ENTRA_CLIENT_ID", "AUTH_MICROSOFT_ENTRA_ID_ID");
  const clientSecret = env("AUTH_ENTRA_CLIENT_SECRET", "AUTH_MICROSOFT_ENTRA_ID_SECRET");
  return Boolean(clientId && clientSecret && issuer);
}

export const entraProviderConfig = {
  issuer,
  authorizeUrl,
  tokenUrl,
  apiScope,
  userFlow,
  clientId: env("AUTH_ENTRA_CLIENT_ID", "AUTH_MICROSOFT_ENTRA_ID_ID"),
  clientSecret: env("AUTH_ENTRA_CLIENT_SECRET", "AUTH_MICROSOFT_ENTRA_ID_SECRET"),
};

export { env as authEnv, apiScope, tokenUrl };
