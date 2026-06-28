import { afterEach, describe, expect, it, vi } from "vitest";

function stubLocation(pathname: string, search = ""): ReturnType<typeof vi.fn> {
  const assign = vi.fn();
  vi.stubGlobal("location", { pathname, search, assign });
  return assign;
}

// The handler keeps a module-scope "redirecting" guard, so each test loads a fresh copy
// to reset it.
async function freshHandler(): Promise<(error: unknown) => void> {
  vi.resetModules();
  return (await import("@/lib/api/on-auth-error")).handleApiAuthError;
}

describe("handleApiAuthError", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("redirects to /sign-in with next on a 401 from a protected page", async () => {
    const assign = stubLocation("/workouts");
    const handle = await freshHandler();
    handle({ status: 401, code: "unauthorized", message: "Session expired." });
    expect(assign).toHaveBeenCalledWith("/sign-in?next=%2Fworkouts");
  });

  it("preserves the query string in next", async () => {
    const assign = stubLocation("/exercises", "?id=abc");
    const handle = await freshHandler();
    handle({ status: 401 });
    expect(assign).toHaveBeenCalledWith("/sign-in?next=%2Fexercises%3Fid%3Dabc");
  });

  it("omits next on the home route", async () => {
    const assign = stubLocation("/");
    const handle = await freshHandler();
    handle({ status: 401 });
    expect(assign).toHaveBeenCalledWith("/sign-in");
  });

  it("ignores non-401 errors and network failures", async () => {
    const assign = stubLocation("/workouts");
    const handle = await freshHandler();
    handle({ status: 500 });
    handle(new TypeError("network"));
    handle(null);
    expect(assign).not.toHaveBeenCalled();
  });

  it("does not redirect from public routes", async () => {
    const assign = stubLocation("/sign-in", "?next=%2Fworkouts");
    const handle = await freshHandler();
    handle({ status: 401 });
    expect(assign).not.toHaveBeenCalled();
  });

  it("redirects only once for a burst of simultaneous 401s", async () => {
    const assign = stubLocation("/analytics");
    const handle = await freshHandler();
    handle({ status: 401 });
    handle({ status: 401 });
    handle({ status: 401 });
    expect(assign).toHaveBeenCalledTimes(1);
  });
});
