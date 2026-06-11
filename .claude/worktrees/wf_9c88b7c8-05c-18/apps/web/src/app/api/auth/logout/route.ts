import { cookies } from "next/headers";
import { NextResponse } from "next/server";

import { callBackend } from "@/lib/auth/backend";
import { ACCESS_COOKIE, clearAuthCookies } from "@/lib/auth/cookies";

export async function POST(): Promise<NextResponse> {
  const access = (await cookies()).get(ACCESS_COOKIE)?.value;

  if (access) {
    await callBackend("/v1/auth/logout", {
      method: "POST",
      headers: { authorization: `Bearer ${access}` },
    }).catch(() => undefined);
  }

  const response = NextResponse.json({ ok: true });
  clearAuthCookies(response);
  return response;
}
