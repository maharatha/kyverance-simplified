/** Protected application routes that require a signed-in session. */
export const PROTECTED_PREFIXES = ["/profile", "/portfolios/mine", "/settings"] as const;

/** Auth.js / NextAuth session cookie names (secure and non-secure variants). */
export const SESSION_COOKIE_NAMES = [
  "authjs.session-token",
  "__Secure-authjs.session-token",
  "next-auth.session-token",
  "__Secure-next-auth.session-token",
] as const;

export function isProtectedPath(pathname: string): boolean {
  return PROTECTED_PREFIXES.some((prefix) => pathname.startsWith(prefix));
}

export function hasSessionCookie(cookieNames: Iterable<string>): boolean {
  const present = new Set(cookieNames);
  return SESSION_COOKIE_NAMES.some((name) => present.has(name));
}
