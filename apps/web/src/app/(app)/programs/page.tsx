"use client";

import { ActiveProgram } from "@/components/programs/active-program";
import { ProgramsOnboarding } from "@/components/programs/onboarding";
import { useMyPrograms } from "@/lib/hooks/programs";

export default function ProgramsPage() {
  const list = useMyPrograms();

  if (list.isLoading) {
    return <p className="text-text-secondary py-10 text-center text-sm">Loading…</p>;
  }
  if (list.isError) {
    return <p className="text-destructive py-10 text-center text-sm">Could not load programs.</p>;
  }

  // First run: no programs yet → onboarding choice. Otherwise the active-program
  // overview (which itself leads with the library when nothing is active).
  if ((list.data?.items ?? []).length === 0) {
    return <ProgramsOnboarding firstRun />;
  }

  return <ActiveProgram />;
}
