"use client";

import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api/client";
import type { components } from "@/lib/api/types";

export type Me = components["schemas"]["MeResponse"];

export function useMe() {
  return useQuery({
    queryKey: ["me"],
    queryFn: () => api.get<Me>("/v1/me"),
    staleTime: 60_000,
    retry: false,
  });
}
