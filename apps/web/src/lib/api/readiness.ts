"use client";

import { api } from "@/lib/api/client";
import { getReadinessToday } from "@/lib/api/today";
import type { components } from "@/lib/api/types";

export type ReadinessHistory = components["schemas"]["ReadinessHistoryResponse"];
export type ReadinessDay = components["schemas"]["ReadinessDay"];

export function getReadinessHistory(params: {
  from: string;
  to: string;
}): Promise<ReadinessHistory> {
  const q = new URLSearchParams();
  q.set("from", params.from);
  q.set("to", params.to);
  return api.get<ReadinessHistory>(`/v1/readiness/history?${q}`);
}

export { getReadinessToday };
