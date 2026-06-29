import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";

// next/navigation is needed by next/link when rendered in jsdom
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), prefetch: vi.fn() }),
  usePathname: () => "/nutrition",
  useSearchParams: () => new URLSearchParams(),
}));

// Stub heavy sub-components so NutritionDay renders without their full deps
vi.mock("@/components/nutrition/calorie-masthead", () => ({
  CalorieMasthead: () => null,
}));

vi.mock("@/components/nutrition/meal-list", () => ({
  MealList: () => null,
}));

vi.mock("@/components/nutrition/nutrition-mode-control", () => ({
  NutritionModeControl: () => null,
}));

vi.mock("@/components/nutrition/quick-add-bar", () => ({
  QuickAddBar: () => null,
}));

vi.mock("@/components/nutrition/recent-chips", () => ({
  RecentChips: () => null,
}));

// Stub the dynamically-imported add-meal sheet
vi.mock("next/dynamic", () => ({
  default: () => () => null,
}));

vi.mock("@/lib/api/nutrition", () => ({
  getFood: vi.fn(),
}));

vi.mock("@/components/ui/toast", () => ({
  useToastStore: vi.fn((selector: (s: unknown) => unknown) => selector({ push: vi.fn() })),
}));

vi.mock("@/lib/hooks/me", () => ({
  useMe: vi.fn(() => ({
    data: { timezone: "UTC", nutrition_mode: "flexible" },
  })),
}));

vi.mock("@/lib/hooks/nutrition", () => ({
  useAddMealItem: vi.fn(() => ({ mutateAsync: vi.fn() })),
  useCompletePlannedMeal: vi.fn(() => ({ mutateAsync: vi.fn() })),
  useCreateMeal: vi.fn(() => ({ mutateAsync: vi.fn(), isPending: false })),
  useDeleteMeal: vi.fn(() => ({ mutate: vi.fn() })),
  useDeleteMealItem: vi.fn(() => ({ mutate: vi.fn() })),
  useMealsRange: vi.fn(() => ({ data: { items: [] }, isLoading: false, isError: false })),
  useRecentFoods: vi.fn(() => ({ data: { items: [] } })),
  useUpdateMealItem: vi.fn(() => ({ mutate: vi.fn() })),
}));

vi.mock("@/lib/hooks/today", () => ({
  useNutritionTargets: vi.fn(() => ({ data: null })),
  useNutritionToday: vi.fn(() => ({ data: null })),
}));

const mockUseActivePlan = vi.fn();
vi.mock("@/lib/hooks/meal-plans", () => ({
  useActivePlan: (...args: unknown[]) => mockUseActivePlan(...args),
}));

// Import after mocks are registered
import { NutritionDay } from "@/components/nutrition/nutrition-day";

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

describe("NutritionDay – Meal plans entry point", () => {
  it('always renders a "Meal plans" link to /nutrition/plans', () => {
    mockUseActivePlan.mockReturnValue({ data: null });

    render(<NutritionDay />, { wrapper });

    const link = screen.getByRole("link", { name: "Meal plans" });
    expect(link).toHaveAttribute("href", "/nutrition/plans");
  });

  it("renders an active-plan chip linking to /nutrition/plans/{id} when a plan is active", () => {
    mockUseActivePlan.mockReturnValue({
      data: {
        plan: { id: "plan-123", name: "High Protein Plan", is_active: true },
        resolved_day: null,
        consumed: {},
        remaining: {},
        date: "2026-06-29",
      },
    });

    render(<NutritionDay />, { wrapper });

    const chipLink = screen.getByRole("link", { name: "High Protein Plan" });
    expect(chipLink).toHaveAttribute("href", "/nutrition/plans/plan-123");
  });

  it("does not render an active-plan chip when no plan is active", () => {
    mockUseActivePlan.mockReturnValue({ data: null });

    render(<NutritionDay />, { wrapper });

    // Only the "Meal plans" library link should be present; no plan-specific link
    const links = screen.getAllByRole("link");
    const planEditorLinks = links.filter((l) =>
      l.getAttribute("href")?.startsWith("/nutrition/plans/"),
    );
    expect(planEditorLinks).toHaveLength(0);
  });
});
