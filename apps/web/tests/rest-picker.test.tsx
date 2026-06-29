import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, within } from "@testing-library/react";

import { RestPicker, secondsToLabel } from "@/components/programs/rest-picker";

describe("secondsToLabel", () => {
  it("formats seconds as M:SS", () => {
    expect(secondsToLabel(15)).toBe("0:15");
    expect(secondsToLabel(90)).toBe("1:30");
    expect(secondsToLabel(600)).toBe("10:00");
  });
});

describe("RestPicker", () => {
  it("shows the current value, or None", () => {
    const { rerender } = render(<RestPicker value={90} onChange={() => {}} />);
    expect(screen.getByRole("button", { name: /1:30/ })).toBeInTheDocument();
    rerender(<RestPicker value={null} onChange={() => {}} />);
    expect(screen.getByRole("button", { name: /None/ })).toBeInTheDocument();
  });

  it("selects a fixed 15s time option", () => {
    const onChange = vi.fn();
    render(<RestPicker value={null} onChange={onChange} />);
    fireEvent.click(screen.getByRole("button", { name: /None/ }));
    const list = screen.getByRole("listbox");
    fireEvent.click(within(list).getByRole("option", { name: "2:00" }));
    expect(onChange).toHaveBeenCalledWith(120);
  });

  it("selects None", () => {
    const onChange = vi.fn();
    render(<RestPicker value={120} onChange={onChange} />);
    fireEvent.click(screen.getByRole("button", { name: /2:00/ }));
    const list = screen.getByRole("listbox");
    fireEvent.click(within(list).getByRole("option", { name: "None" }));
    expect(onChange).toHaveBeenCalledWith(null);
  });
});
