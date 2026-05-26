/**
 * Browser-side API client. Calls our Next.js proxy at /api/proxy/<backend-path>.
 * The proxy reads the httpOnly access cookie, forwards to the FastAPI backend,
 * and refreshes once on 401.
 */

export interface ApiError {
  status: number;
  code: string;
  message: string;
  details?: unknown;
}

async function request<T>(
  method: "GET" | "POST" | "PATCH" | "DELETE",
  path: string,
  body?: unknown,
): Promise<T> {
  const url = `/api/proxy${path.startsWith("/") ? path : `/${path}`}`;
  const response = await fetch(url, {
    method,
    credentials: "include",
    headers: { "content-type": "application/json" },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  if (response.status === 204) {
    return undefined as T;
  }

  const text = await response.text();
  const payload: unknown = text ? JSON.parse(text) : null;

  if (!response.ok) {
    const err = (payload as { error?: { code?: string; message?: string; details?: unknown } })
      ?.error;
    const apiError: ApiError = {
      status: response.status,
      code: err?.code ?? "internal_error",
      message: err?.message ?? `Request failed with ${response.status}`,
      details: err?.details,
    };
    throw apiError;
  }

  return payload as T;
}

export const api = {
  get: <T>(path: string) => request<T>("GET", path),
  post: <T>(path: string, body?: unknown) => request<T>("POST", path, body),
  patch: <T>(path: string, body?: unknown) => request<T>("PATCH", path, body),
  delete: <T>(path: string) => request<T>("DELETE", path),
};
