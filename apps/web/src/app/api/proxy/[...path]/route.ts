import { cookies } from "next/headers";
import { NextResponse } from "next/server";

import { callBackend } from "@/lib/auth/backend";
import {
  ACCESS_COOKIE,
  REFRESH_COOKIE,
  clearAuthCookies,
  setAuthCookies,
} from "@/lib/auth/cookies";

type Method = "GET" | "POST" | "PATCH" | "DELETE";

interface ProxyContext {
  params: Promise<{ path: string[] }>;
}

async function readBody(request: Request): Promise<string | undefined> {
  if (request.method === "GET" || request.method === "DELETE") return undefined;
  const text = await request.text();
  return text.length > 0 ? text : undefined;
}

async function forward(
  backendPath: string,
  method: Method,
  body: string | undefined,
  accessToken: string | undefined,
  search: string,
): Promise<Response> {
  const fullPath = `${backendPath}${search}`;
  const headers: Record<string, string> = { "content-type": "application/json" };
  if (accessToken) headers.authorization = `Bearer ${accessToken}`;
  return callBackend(fullPath, {
    method,
    headers,
    body: body ? JSON.parse(body) : undefined,
  });
}

type RefreshResult =
  | { ok: true; access: string; refresh: string; expiresIn: number }
  | { ok: false };

// Coalesce concurrent refreshes of the same token. A cold tab fires several queries at
// once, each hitting an expired access cookie and trying to refresh the *same* refresh
// token; without this they would race the backend's single-use rotation. Within one Node
// instance this collapses the burst to a single /v1/auth/refresh so they all reuse the
// rotated pair. (The backend's rotation grace window covers bursts that span instances.)
const inflightRefresh = new Map<string, Promise<RefreshResult>>();

async function doRefresh(refresh: string): Promise<RefreshResult> {
  const upstream = await callBackend("/v1/auth/refresh", {
    method: "POST",
    body: { refresh_token: refresh },
  });
  if (!upstream.ok) return { ok: false };
  const json = (await upstream.json()) as {
    access_token?: string;
    refresh_token?: string;
    expires_in?: number;
  };
  if (!json.access_token || !json.refresh_token) return { ok: false };
  return {
    ok: true,
    access: json.access_token,
    refresh: json.refresh_token,
    expiresIn: json.expires_in ?? 0,
  };
}

function refreshOnce(refresh: string): Promise<RefreshResult> {
  const existing = inflightRefresh.get(refresh);
  if (existing) return existing;
  const pending = doRefresh(refresh).finally(() => {
    inflightRefresh.delete(refresh);
  });
  inflightRefresh.set(refresh, pending);
  return pending;
}

async function handle(method: Method, request: Request, context: ProxyContext): Promise<Response> {
  const { path } = await context.params;
  const backendPath = `/${path.join("/")}`;
  const search = new URL(request.url).search;
  const body = await readBody(request);

  const cookieStore = await cookies();
  let access = cookieStore.get(ACCESS_COOKIE)?.value;
  const refresh = cookieStore.get(REFRESH_COOKIE)?.value;

  let upstream = await forward(backendPath, method, body, access, search);

  let refreshed: { access: string; refresh: string; expiresIn: number } | null = null;
  if (upstream.status === 401) {
    const result: RefreshResult = refresh ? await refreshOnce(refresh) : { ok: false };
    if (result.ok) {
      refreshed = { access: result.access, refresh: result.refresh, expiresIn: result.expiresIn };
      access = refreshed.access;
      upstream = await forward(backendPath, method, body, access, search);
    } else {
      const cleared = NextResponse.json(
        { error: { code: "unauthorized", message: "Session expired." } },
        { status: 401 },
      );
      clearAuthCookies(cleared);
      return cleared;
    }
  }

  const responseText = await upstream.text();
  const response = new NextResponse(responseText.length > 0 ? responseText : null, {
    status: upstream.status,
    headers: {
      "content-type": upstream.headers.get("content-type") ?? "application/json",
    },
  });

  if (refreshed) {
    setAuthCookies(response as NextResponse, {
      access_token: refreshed.access,
      refresh_token: refreshed.refresh,
      expires_in: refreshed.expiresIn,
    });
  }

  return response;
}

export async function GET(request: Request, context: ProxyContext): Promise<Response> {
  return handle("GET", request, context);
}
export async function POST(request: Request, context: ProxyContext): Promise<Response> {
  return handle("POST", request, context);
}
export async function PATCH(request: Request, context: ProxyContext): Promise<Response> {
  return handle("PATCH", request, context);
}
export async function DELETE(request: Request, context: ProxyContext): Promise<Response> {
  return handle("DELETE", request, context);
}
