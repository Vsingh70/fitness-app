import { serverEnv } from "@/lib/env";

interface BackendCallOpts {
  method?: "GET" | "POST" | "PATCH" | "DELETE";
  body?: unknown;
  headers?: Record<string, string>;
}

export async function callBackend(path: string, opts: BackendCallOpts = {}): Promise<Response> {
  const { backendUrl } = serverEnv();
  const url = new URL(path, backendUrl).toString();
  const headers: Record<string, string> = {
    "content-type": "application/json",
    ...(opts.headers ?? {}),
  };
  return fetch(url, {
    method: opts.method ?? "GET",
    headers,
    body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined,
    cache: "no-store",
  });
}
