import { NextResponse } from "next/server";
import { z } from "zod";

import { callBackend } from "@/lib/auth/backend";
import { setAuthCookies } from "@/lib/auth/cookies";

const bodySchema = z.object({ id_token: z.string().min(1) });

export async function POST(request: Request): Promise<NextResponse> {
  const parsed = bodySchema.safeParse(await request.json().catch(() => ({})));
  if (!parsed.success) {
    return NextResponse.json(
      { error: { code: "validation_error", message: "id_token required" } },
      { status: 400 },
    );
  }

  const upstream = await callBackend("/v1/auth/apple", {
    method: "POST",
    body: { id_token: parsed.data.id_token },
  });
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
