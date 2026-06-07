"use client";

import { useQuery } from "@tanstack/react-query";

import * as api from "@/lib/api/readiness";

/** local YYYY-MM-DD for a Date (no UTC shift — uses local calendar day). */
function isoDay(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

export function useReadinessHistory(days = 30) {
  const to = new Date();
  const from = new Date();
  from.setDate(from.getDate() - (days - 1)); // inclusive window of `days` days
  const range = { from: isoDay(from), to: isoDay(to) };

  return useQuery({
    queryKey: ["readiness", "history", { days }] as const,
    queryFn: () => api.getReadinessHistory(range),
    staleTime: 60_000,
  });
}
