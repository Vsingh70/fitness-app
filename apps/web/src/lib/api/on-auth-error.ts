/**
 * Centralized reaction to a 401 from the API proxy.
 *
 * The proxy only surfaces a 401 to the browser once a refresh has genuinely failed (and
 * it has already cleared the auth cookies), so a 401 reaching here means the session is
 * dead. We send the user to /sign-in consistently. Previously only the Settings page did
 * this, so an expired session left every other page stranded on an inline error
 * ("workouts not loading") until the user happened to open Settings.
 *
 * Wired into the TanStack QueryCache/MutationCache onError in providers.tsx, so it covers
 * every query and mutation regardless of which api module made the call (they all throw
 * the same ApiError shape).
 */
import type { ApiError } from "@/lib/api/client";

// Mirrors PUBLIC_PREFIXES in middleware.ts — routes reachable while signed out, where a
// background 401 must NOT redirect (avoids redirect loops and interrupting OAuth flows).
const PUBLIC_PREFIXES = ["/sign-in", "/callback", "/integrations"];

// A single page mounts several queries that can all 401 in the same tick; this guard
// collapses that burst into one navigation.
let redirecting = false;

export function handleApiAuthError(error: unknown): void {
  if (typeof window === "undefined") return;
  if ((error as Partial<ApiError> | null)?.status !== 401) return;

  const { pathname, search } = window.location;
  if (PUBLIC_PREFIXES.some((p) => pathname === p || pathname.startsWith(`${p}/`))) return;

  if (redirecting) return;
  redirecting = true;

  // Preserve where the user was so sign-in can return them (mirrors the middleware,
  // which omits `next` for the home route).
  const next = `${pathname}${search}`;
  const target = pathname === "/" ? "/sign-in" : `/sign-in?next=${encodeURIComponent(next)}`;
  window.location.assign(target);
}
