/**
 * Tests for weight-unit support across exercise detail, PR tiles,
 * predicted-next strip, and plate calculator.
 */

import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";

// ---------------------------------------------------------------------------
// Module mocks
// ---------------------------------------------------------------------------

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), prefetch: vi.fn() }),
  usePathname: () => "/exercises/ex-1",
  useSearchParams: () => new URLSearchParams(),
}));

const mockUseMe = vi.fn(() => ({
  data: { unit_system: "metric" as "metric" | "imperial" },
  isLoading: false,
  isError: false,
}));

vi.mock("@/lib/hooks/me", () => ({
  useMe: () => mockUseMe(),
}));

const mockUseExerciseAnalytics = vi.fn();

vi.mock("@/lib/hooks/analytics", () => ({
  useExerciseAnalytics: (...args: unknown[]) => mockUseExerciseAnalytics(...args),
}));

// ---------------------------------------------------------------------------
// Imports (after mocks)
// ---------------------------------------------------------------------------

import { ExerciseDetailView } from "@/app/(app)/exercises/[id]/exercise-detail-view";
import { PrTileRow } from "@/components/exercise/pr-tile-row";
import { PredictedNextStrip } from "@/components/exercise/predicted-next-strip";
import { PlateMathStrip } from "@/components/workouts/plate-math";
import type { components } from "@/lib/api/types";

type PRRow = components["schemas"]["PRRowResponse"];
type ScatterPoint = components["schemas"]["ScatterPointResponse"];
type Predicted = components["schemas"]["PredictedNextSessionResponse"];

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const PR_ROW: PRRow = {
  e1rm_kg: "100",
  reps: 5,
  session_date: "2025-01-01",
  weight_kg: "80",
};

const SCATTER: ScatterPoint = {
  is_pr: false,
  reps: 5,
  rpe: null,
  session_date: "2025-01-01",
  weight_kg: "80",
};

const PREDICTED: Predicted = {
  has_prediction: true,
  is_deload: false,
  kind: "increase_weight",
  rationale: null,
  rationale_key: null,
  source: "algo",
  suggested_reps_high: 5,
  suggested_reps_low: 3,
  // 82.5 kg * 2.20462 = 181.881... → round1 = 181.9 lb
  suggested_weight_kg: "82.5",
};

const ANALYTICS_DATA = {
  avg_rpe_series: [],
  e1rm_series: [{ session_date: "2025-01-01", value: "100" }],
  exercise: {
    id: "ex-1",
    name: "Squat",
    slug: "squat",
    tracking_type: "weight_reps",
    equipment: "barbell",
    movement_pattern: "squat",
    primary_muscle: "quads",
    secondary_muscles: [],
    is_unilateral: false,
    owner_id: null,
    archived_at: null,
    created_at: "2024-01-01T00:00:00Z",
    updated_at: "2024-01-01T00:00:00Z",
  },
  predicted_next_session: PREDICTED,
  recent_prs: [PR_ROW],
  set_scatter: [{ ...SCATTER, weight_kg: "80" }],
  suggested_variants: [],
  volume_series: [{ session_date: "2025-01-01", value: "500" }],
  window: "12w",
};

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

// ---------------------------------------------------------------------------
// PrTileRow — unit prop
// ---------------------------------------------------------------------------

describe("PrTileRow unit prop", () => {
  it("metric: shows e1RM and weight in kg", () => {
    render(<PrTileRow recentPrs={[PR_ROW]} setScatter={[SCATTER]} unit="metric" />);
    // 100 kg e1RM → "100" with "kg" label; 80 kg heaviest → "80" with "kg"
    expect(screen.getByText("100")).toBeInTheDocument();
    expect(screen.getAllByText("kg").length).toBeGreaterThan(0);
    // must NOT show lb
    expect(screen.queryByText("lb")).toBeNull();
  });

  it("imperial: shows e1RM and weight in lb (converted from kg)", () => {
    render(<PrTileRow recentPrs={[PR_ROW]} setScatter={[SCATTER]} unit="imperial" />);
    // 100 kg → 220.5 lb (e1RM), 80 kg → 176.4 lb (heaviest)
    expect(screen.getByText("220.5")).toBeInTheDocument();
    expect(screen.getByText("176.4")).toBeInTheDocument();
    // unit label must be lb
    expect(screen.getAllByText("lb").length).toBeGreaterThan(0);
    // no raw kg unit label
    expect(screen.queryByText("kg")).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// PredictedNextStrip — unit prop
// ---------------------------------------------------------------------------

describe("PredictedNextStrip unit prop", () => {
  it("metric: shows suggested weight in kg", () => {
    render(<PredictedNextStrip predicted={PREDICTED} unit="metric" />);
    // "Try 82.5 kg"
    expect(screen.getByText(/82\.5 kg/)).toBeInTheDocument();
  });

  it("imperial: shows suggested weight in lb (converted)", () => {
    render(<PredictedNextStrip predicted={PREDICTED} unit="imperial" />);
    // 82.5 kg * 2.20462 = 181.881... → round1 = 181.9 lb
    expect(screen.getByText(/181\.9 lb/)).toBeInTheDocument();
    // must not show the raw kg value
    expect(screen.queryByText(/82\.5 kg/)).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// PlateMathStrip — unit prop
// ---------------------------------------------------------------------------

describe("PlateMathStrip unit prop", () => {
  it("metric: shows the target in kg and the per-side amount without lb", () => {
    // 60 kg: bar=20 kg, per side = 20 kg. Summary: "60 kg · 20 per side"
    render(<PlateMathStrip targetKg={60} unit="metric" />);
    // The summary span shows "60 kg · 20 per side"
    expect(screen.getByText(/60 kg/i)).toBeInTheDocument();
    // Should not show lb anywhere
    expect(screen.queryByText(/lb/i)).toBeNull();
  });

  it("imperial: shows the target in lb (converted) and uses lb label", () => {
    // 100 kg → 220.5 lb. bar=45 lb. Summary: "220.5 lb · 87.75 per side"
    render(<PlateMathStrip targetKg={100} unit="imperial" />);
    // The summary shows 220.5 lb (the converted display target)
    expect(screen.getByText(/220\.5 lb/i)).toBeInTheDocument();
    // Should NOT show 100 kg anywhere
    expect(screen.queryByText(/100 kg/i)).toBeNull();
  });

  it("metric: just the bar shows 20 kg for a target at or below bar", () => {
    render(<PlateMathStrip targetKg={20} unit="metric" />);
    expect(screen.getByText(/just the bar · 20 kg/i)).toBeInTheDocument();
  });

  it("imperial: just the bar shows 45 lb for a target that converts to <= 45 lb", () => {
    // 20 kg → 44.1 lb < 45 lb bar → "Just the bar · 45 lb"
    render(<PlateMathStrip targetKg={20} unit="imperial" />);
    expect(screen.getByText(/just the bar · 45 lb/i)).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// ExerciseDetailView — imperial via useMe mock
// ---------------------------------------------------------------------------

describe("ExerciseDetailView imperial unit via useMe", () => {
  beforeEach(() => {
    mockUseExerciseAnalytics.mockReturnValue({
      data: ANALYTICS_DATA,
      isLoading: false,
      isError: false,
    });
  });

  it("all-sets table shows weight in lb (converted) with lb header", () => {
    mockUseMe.mockReturnValue({
      data: { unit_system: "imperial" as const },
      isLoading: false,
      isError: false,
    });

    render(<ExerciseDetailView id="ex-1" />, { wrapper });

    // Click "Sets" tab (role="tab") to see the table
    const setsTab = screen.getByRole("tab", { name: /sets/i });
    fireEvent.click(setsTab);

    // Column header should include "lb"
    expect(screen.getByText(/Weight \(lb\)/i)).toBeInTheDocument();

    // 80 kg → 176.4 lb — appears in table cell (may also appear in PR tiles)
    expect(screen.getByRole("cell", { name: "176.4" })).toBeInTheDocument();

    // Weight (kg) header should not appear
    expect(screen.queryByText(/Weight \(kg\)/i)).toBeNull();
  });

  it("all-sets table shows weight in kg with kg header when metric", () => {
    mockUseMe.mockReturnValue({
      data: { unit_system: "metric" as const },
      isLoading: false,
      isError: false,
    });

    render(<ExerciseDetailView id="ex-1" />, { wrapper });

    const setsTab = screen.getByRole("tab", { name: /sets/i });
    fireEvent.click(setsTab);

    expect(screen.getByText(/Weight \(kg\)/i)).toBeInTheDocument();
    // 80 kg stays 80 — check the table cell specifically
    expect(screen.getByRole("cell", { name: "80" })).toBeInTheDocument();
    expect(screen.queryByText(/Weight \(lb\)/i)).toBeNull();
  });
});
