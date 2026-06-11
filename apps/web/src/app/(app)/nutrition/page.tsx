"use client";

import { NutritionDay } from "@/components/nutrition/nutrition-day";
import { NutritionOnboarding } from "@/components/nutrition/onboarding";
import { useMe } from "@/lib/hooks/me";

export default function NutritionPage() {
  const me = useMe();

  if (me.isLoading) {
    return <p className="text-text-secondary py-10 text-center text-sm">Loading…</p>;
  }
  if (me.isError) {
    return (
      <p className="text-destructive py-10 text-center text-sm">Could not load your profile.</p>
    );
  }

  // First run: gate on the field being null (not a one-time flag), so resetting
  // nutrition_mode brings the onboarding back.
  if (me.data?.nutrition_mode == null) {
    return <NutritionOnboarding />;
  }

  return <NutritionDay />;
}
