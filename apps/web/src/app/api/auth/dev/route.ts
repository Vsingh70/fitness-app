import { NextResponse } from "next/server";
import { z } from "zod";

import { callBackend } from "@/lib/auth/backend";
import { setAuthCookies } from "@/lib/auth/cookies";

const bodySchema = z.object({
  sub: z.string().min(1).max(128),
  email: z.string().optional(),
});

export async function POST(request: Request): Promise<NextResponse> {
  if (process.env.ENVIRONMENT === "prod") {
    return NextResponse.json({ error: { code: "not_found", message: "" } }, { status: 404 });
  }
  const parsed = bodySchema.safeParse(await request.json().catch(() => ({})));
  if (!parsed.success) {
    return NextResponse.json(
      { error: { code: "validation_error", message: "sub required" } },
      { status: 400 },
    );
  }

  const upstream = await callBackend("/v1/auth/dev", { method: "POST", body: parsed.data });
  const payload = (await upstream.json().catch(() => null)) as
    | { access_token?: string; refresh_token?: string; expires_in?: number }
    | { error?: unknown }
    | null;

  if (!upstream.ok || !payload || !("access_token" in payload) || !payload.access_token) {
    return NextResponse.json(payload ?? { error: { code: "internal_error", message: "" } }, {
      status: upstream.status,
    });
  }

  const response = NextResponse.json({ ok: true });
  setAuthCookies(response, {
    access_token: payload.access_token,
    refresh_token: payload.refresh_token ?? "",
    expires_in: payload.expires_in ?? 0,
  });
  return response;
}
