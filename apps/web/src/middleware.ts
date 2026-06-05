import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

import { ACCESS_COOKIE, REFRESH_COOKIE } from "@/lib/auth/cookies";

/**
 * UX auth gate (not the security boundary — the backend enforces auth on every
 * API call). Redirects unauthenticated visitors of protected pages to /sign-in,
 * and bounces already-signed-in users away from /sign-in.
 *
 * "Authenticated" = presence of either the short-lived access cookie or the
 * long-lived refresh cookie. The /api/proxy route transparently refreshes the
 * access token using the refresh cookie, so a stale access token still counts
 * as signed in.
 */

const PUBLIC_PREFIXES = ["/sign-in", "/callback", "/integrations"];

export function middleware(request: NextRequest): NextResponse {
  const { pathname } = request.nextUrl;
  const cookies = request.cookies;
  const isAuthed = cookies.has(ACCESS_COOKIE) || cookies.has(REFRESH_COOKIE);

  const isPublic = PUBLIC_PREFIXES.some(
    (p) => pathname === p || pathname.startsWith(`${p}/`),
  );

  // Signed-in user landing on the sign-in page → send them into the app.
  if (isAuthed && pathname === "/sign-in") {
    return NextResponse.redirect(new URL("/", request.url));
  }

  // Unauthenticated user on a protected page → send them to sign-in, preserving
  // where they were headed so we can return them after login.
  if (!isAuthed && !isPublic) {
    const signInUrl = new URL("/sign-in", request.url);
    if (pathname !== "/") {
      signInUrl.searchParams.set("next", pathname);
    }
    return NextResponse.redirect(signInUrl);
  }

  return NextResponse.next();
}

export const config = {
  // Run on everything except API routes, Next internals, and static assets.
  // The /api/proxy + /api/auth routes must stay reachable for the auth flow.
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico|.*\\..*).*)"],
};
