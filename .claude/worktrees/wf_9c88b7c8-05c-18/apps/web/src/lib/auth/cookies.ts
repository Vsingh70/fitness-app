import type { NextResponse } from "next/server";
import { serverEnv } from "@/lib/env";

export const ACCESS_COOKIE = "gym_access";
export const REFRESH_COOKIE = "gym_refresh";

const FIFTEEN_MIN = 15 * 60;
const SIXTY_DAYS = 60 * 24 * 60 * 60;

interface TokenPair {
  access_token: string;
  refresh_token: string;
  expires_in: number;
}

export function setAuthCookies(response: NextResponse, tokens: TokenPair): void {
  const { cookieSecure, cookieDomain } = serverEnv();
  const common = {
    httpOnly: true,
    sameSite: "lax" as const,
    secure: cookieSecure,
    path: "/",
    ...(cookieDomain ? { domain: cookieDomain } : {}),
  };
  response.cookies.set(ACCESS_COOKIE, tokens.access_token, {
    ...common,
    maxAge: tokens.expires_in || FIFTEEN_MIN,
  });
  response.cookies.set(REFRESH_COOKIE, tokens.refresh_token, {
    ...common,
    maxAge: SIXTY_DAYS,
  });
}

export function clearAuthCookies(response: NextResponse): void {
  const { cookieDomain } = serverEnv();
  const common = {
    path: "/",
    maxAge: 0,
    ...(cookieDomain ? { domain: cookieDomain } : {}),
  };
  response.cookies.set(ACCESS_COOKIE, "", common);
  response.cookies.set(REFRESH_COOKIE, "", common);
}
