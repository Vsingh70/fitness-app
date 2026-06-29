import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";

// next/navigation is needed by next/link when rendered in jsdom
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), prefetch: vi.fn() }),
  usePathname: () => "/settings",
  useSearchParams: () => new URLSearchParams(),
}));

vi.mock("@/lib/hooks/me", () => ({
  useMe: vi.fn(() => ({
    data: {
      id: "u1",
      email: "test@test.com",
      display_name: "Test User",
      birthdate: null,
      timezone: "UTC",
      unit_system: "metric",
      nutrition_mode: "flexible",
    },
    isLoading: false,
    isError: false,
    error: null,
    refetch: vi.fn(),
  })),
  useUpdateMe: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
  useDeleteAccount: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
}));

vi.mock("@/lib/hooks/programs", () => ({
  useMyPrograms: vi.fn(() => ({ data: { items: [] }, isLoading: false, refetch: vi.fn() })),
  useDeactivateAnyProgram: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
}));

vi.mock("@/lib/hooks/health", () => ({
  useHealthStatus: vi.fn(() => ({ data: null, isLoading: false })),
}));

vi.mock("@/lib/hooks/use-prefs", () => ({
  usePrefs: vi.fn(() => ({
    distance: "km",
    density: "regular",
    restTimerSeconds: 120,
    setPref: vi.fn(),
  })),
}));

vi.mock("@/lib/hooks/use-theme", () => ({
  ACCENTS: ["blue", "indigo", "mint", "orange", "pink"],
  useThemeStore: vi.fn((selector?: (s: unknown) => unknown) => {
    const state = { theme: "system", accent: "blue", setTheme: vi.fn(), setAccent: vi.fn() };
    return selector ? selector(state) : state;
  }),
}));

const mockDeactivateMutate = vi.fn();
vi.mock("@/lib/hooks/meal-plans", () => ({
  useMealPlans: vi.fn(),
  useDeactivateAnyMealPlan: vi.fn(() => ({ mutate: mockDeactivateMutate, isPending: false })),
}));

const mockPushToast = vi.fn();
vi.mock("@/components/ui/toast", () => ({
  useToastStore: vi.fn((selector: (s: unknown) => unknown) => selector({ push: mockPushToast })),
}));

// Import after mocks are registered
import { useMealPlans } from "@/lib/hooks/meal-plans";
import SettingsPage from "@/app/(app)/settings/page";

function plan(overrides: Record<string, unknown> = {}) {
  return {
    id: "mp1",
    name: "High Protein Plan",
    is_active: true,
    activated_at: "2026-06-01T00:00:00Z",
    kind: "daily_repeating",
    content_mode: "targets_and_meals",
    tracking_mode: "macros_and_calories",
    created_at: "2026-05-01T00:00:00Z",
    ...overrides,
  };
}

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

describe("Settings – Active meal plan section", () => {
  beforeEach(() => {
    mockDeactivateMutate.mockReset();
    mockPushToast.mockReset();
  });

  it("shows the plan name and Deactivate button when an active plan exists", async () => {
    vi.mocked(useMealPlans).mockReturnValue({
      data: { items: [plan()] },
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useMealPlans>);

    const user = userEvent.setup();
    render(<SettingsPage />, { wrapper });

    expect(screen.getByText("High Protein Plan")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Deactivate" }));

    expect(mockDeactivateMutate).toHaveBeenCalledWith("mp1", expect.any(Object));
  });

  it("shows Browse meal plans link to /nutrition/plans when no plan is active", () => {
    vi.mocked(useMealPlans).mockReturnValue({
      data: { items: [plan({ is_active: false })] },
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useMealPlans>);

    render(<SettingsPage />, { wrapper });

    const link = screen.getByRole("link", { name: "Browse meal plans" });
    expect(link).toHaveAttribute("href", "/nutrition/plans");
  });
});
