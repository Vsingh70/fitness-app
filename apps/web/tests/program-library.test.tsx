import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";

import { ProgramLibrary } from "@/components/programs/program-library";
import type { ProgramListItem } from "@/lib/programs/types";

const push = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push, replace: vi.fn(), prefetch: vi.fn() }),
}));

function item(overrides: Partial<ProgramListItem> = {}): ProgramListItem {
  return {
    id: "p1",
    name: "Push Pull Legs",
    goal: "hypertrophy",
    microcycle_length: 6,
    mesocycle_length_microcycles: 4,
    is_active: false,
    activated_at: null,
    created_at: "2026-01-01T00:00:00Z",
    source: "manual",
    ...overrides,
  };
}

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

describe("ProgramLibrary", () => {
  beforeEach(() => {
    push.mockReset();
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders the microcycle + mesocycle length + goal meta line", () => {
    render(<ProgramLibrary items={[item()]} />, { wrapper });
    expect(screen.getByText("6-slot cycle · 4 micro · hypertrophy")).toBeInTheDocument();
  });

  it("humanizes a multi-word goal in the meta", () => {
    render(<ProgramLibrary items={[item({ goal: "fat_loss" })]} />, { wrapper });
    expect(screen.getByText(/fat loss$/)).toBeInTheDocument();
  });

  it("inactive program shows Activate; active program shows Active + Deactivate", () => {
    const { rerender } = render(<ProgramLibrary items={[item()]} />, { wrapper });
    expect(screen.getByRole("button", { name: "Activate" })).toBeInTheDocument();

    rerender(<ProgramLibrary items={[item({ is_active: true })]} />);
    expect(screen.getByText("Active")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Deactivate" })).toBeInTheDocument();
  });

  it("overflow menu exposes Duplicate and Save as template", async () => {
    const user = userEvent.setup();
    render(<ProgramLibrary items={[item()]} />, { wrapper });
    await user.click(screen.getByRole("button", { name: /more actions/i }));
    const menu = screen.getByRole("menu");
    expect(within(menu).getByRole("menuitem", { name: /duplicate/i })).toBeInTheDocument();
    expect(within(menu).getByRole("menuitem", { name: /save as template/i })).toBeInTheDocument();
    // Deactivate only appears in the menu for an active program (touch reach).
    expect(within(menu).queryByRole("menuitem", { name: /deactivate/i })).toBeNull();
  });

  it("active program's overflow menu adds a Deactivate item for touch", async () => {
    const user = userEvent.setup();
    render(<ProgramLibrary items={[item({ is_active: true })]} />, { wrapper });
    await user.click(screen.getByRole("button", { name: /more actions/i }));
    const menu = screen.getByRole("menu");
    expect(within(menu).getByRole("menuitem", { name: /deactivate/i })).toBeInTheDocument();
  });

  it("Duplicate posts and routes to the new copy's builder", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({ program: { ...item({ id: "p2", name: "Push Pull Legs (copy)" }) } }),
        {
          status: 200,
          headers: { "content-type": "application/json" },
        },
      ),
    );
    render(<ProgramLibrary items={[item()]} />, { wrapper });
    await user.click(screen.getByRole("button", { name: /more actions/i }));
    await user.click(screen.getByRole("menuitem", { name: /duplicate/i }));

    await waitFor(() => expect(push).toHaveBeenCalledWith("/programs/p2/edit"));
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/proxy/v1/programs/p1/duplicate",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("Save as template opens a dialog with name + visibility and posts", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ template: { slug: "x" } }), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    );
    render(<ProgramLibrary items={[item()]} />, { wrapper });
    await user.click(screen.getByRole("button", { name: /more actions/i }));
    await user.click(screen.getByRole("menuitem", { name: /save as template/i }));

    const dialog = await screen.findByRole("dialog");
    // Visibility defaults to Private; switch to Shared then save.
    await user.click(within(dialog).getByRole("button", { name: /shared with partners/i }));
    await user.click(within(dialog).getByRole("button", { name: /save template/i }));

    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/proxy/v1/programs/p1/save-as-template",
        expect.objectContaining({ method: "POST" }),
      ),
    );
    const body = JSON.parse((fetchMock.mock.calls[0]![1] as RequestInit).body as string);
    expect(body).toMatchObject({ name: "Push Pull Legs template", visibility: "shared" });
  });

  it("dashed create button routes to the new-program chooser", () => {
    render(<ProgramLibrary items={[item()]} />, { wrapper });
    expect(screen.getByRole("link", { name: /create a new program/i })).toHaveAttribute(
      "href",
      "/programs/new",
    );
  });
});
