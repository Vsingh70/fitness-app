import { afterEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";

import { Sheet } from "@/components/ui/motion-sheet";

afterEach(() => {
  document.body.style.overflow = "";
});

describe("motion Sheet", () => {
  it("renders children in a labelled dialog when open", () => {
    render(
      <Sheet open onOpenChange={() => {}} title="Add exercise">
        <button>Inside</button>
      </Sheet>,
    );
    expect(screen.getByRole("dialog", { name: "Add exercise" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Inside" })).toBeInTheDocument();
  });

  it("renders nothing when closed", () => {
    render(
      <Sheet open={false} onOpenChange={() => {}}>
        <button>Inside</button>
      </Sheet>,
    );
    expect(screen.queryByText("Inside")).toBeNull();
  });

  it("locks body scroll while open and restores it on close", () => {
    const { unmount } = render(
      <Sheet open onOpenChange={() => {}}>
        <button>Inside</button>
      </Sheet>,
    );
    expect(document.body.style.overflow).toBe("hidden");
    unmount();
    expect(document.body.style.overflow).toBe("");
  });

  it("moves focus into the panel on open", async () => {
    render(
      <Sheet open onOpenChange={() => {}}>
        <input aria-label="search" />
      </Sheet>,
    );
    // Focus is deferred to a requestAnimationFrame so it doesn't stutter the
    // entrance animation.
    await waitFor(() => expect(screen.getByLabelText("search")).toHaveFocus());
  });

  it("closes on Escape", () => {
    const onOpenChange = vi.fn();
    render(
      <Sheet open onOpenChange={onOpenChange}>
        <button>Inside</button>
      </Sheet>,
    );
    fireEvent.keyDown(document, { key: "Escape" });
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });
});
