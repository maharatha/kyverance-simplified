import type { NextAuthConfig } from "next-auth";
import { isProtectedPath } from "./lib/auth-routes";

/**
 * Edge-compatible Auth.js config fragment (no Node Buffer, Jose refresh, or providers).
 * Full Node runtime configuration lives in `auth.ts`.
 */
export const authConfig = {
  trustHost: true,
  pages: {
    signIn: "/sign-in",
  },
  providers: [],
  callbacks: {
    authorized({ auth, request }) {
      const { pathname } = request.nextUrl;
      if (pathname.startsWith("/api/auth")) return true;
      if (pathname === "/sign-in") return true;
      if (pathname === "/") return true;
      if (!isProtectedPath(pathname)) return true;
      if (auth?.error) return false;
      return Boolean(auth?.user?.id || auth?.accessToken || auth?.isDev);
    },
  },
} satisfies NextAuthConfig;

export {
  entraProviderConfig,
  isEntraConfigured,
  isLocalDevIdentityEnabled,
  resolveAuthSecret,
} from "./lib/auth-env";

export { PROTECTED_PREFIXES } from "./lib/auth-routes";
