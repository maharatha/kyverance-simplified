import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import { hasSessionCookie, isProtectedPath } from "./lib/auth-routes";

/**
 * Edge-safe route gate: cookie presence only (no Auth.js / Jose imports).
 * Protected pages still call `auth()` in the Node runtime for fail-closed validation.
 */
export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  if (pathname.startsWith("/api/auth")) {
    return NextResponse.next();
  }

  if (!isProtectedPath(pathname)) {
    return NextResponse.next();
  }

  const cookieNames = request.cookies.getAll().map((cookie) => cookie.name);
  if (hasSessionCookie(cookieNames)) {
    return NextResponse.next();
  }

  const signIn = request.nextUrl.clone();
  signIn.pathname = "/sign-in";
  signIn.search = "";
  signIn.searchParams.set(
    "callbackUrl",
    `${request.nextUrl.pathname}${request.nextUrl.search}`,
  );
  return NextResponse.redirect(signIn);
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)"],
};
