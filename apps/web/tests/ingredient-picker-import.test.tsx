import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

vi.mock("@/lib/api/nutrition", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api/nutrition")>();
  return { ...actual, parseFoodUrl: vi.fn() };
});

import { IngredientPicker } from "@/components/nutrition/ingredient-picker";
import { parseFoodUrl } from "@/lib/api/nutrition";

describe("IngredientPicker — manual URL import", () => {
  beforeEach(() => vi.clearAllMocks());

  it("populates the manual form from a parsed URL", async () => {
    vi.mocked(parseFoodUrl).mockResolvedValue({
      name: "Protein Pancakes",
      brand: null,
      serving_label: "1 serving (150 g)",
      serving_grams: "150",
      kcal: "320",
      protein_g: "24",
      carbs_g: "40",
      fat_g: "8",
      fiber_g: "5",
      source_url: "https://example.com/r",
      warning: null,
    });
    const user = userEvent.setup();
    render(
      <IngredientPicker
        open
        title="Add"
        initialTab="manual"
        onClose={() => {}}
        onPick={() => {}}
      />,
    );

    await user.type(screen.getByPlaceholderText(/recipe or product url/i), "https://example.com/r");
    await user.click(screen.getByRole("button", { name: /fetch/i }));

    await waitFor(() =>
      expect(screen.getByPlaceholderText("e.g. Oats")).toHaveValue("Protein Pancakes"),
    );
    expect(parseFoodUrl).toHaveBeenCalledWith("https://example.com/r");
    // Macros + amount (g) prefilled from the per-serving parse.
    expect(screen.getByDisplayValue("320")).toBeInTheDocument(); // kcal
    expect(screen.getByDisplayValue("150")).toBeInTheDocument(); // amount (g)
  });
});
