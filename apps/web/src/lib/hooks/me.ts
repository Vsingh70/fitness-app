"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api/client";
import type { components } from "@/lib/api/types";

export type Me = components["schemas"]["MeResponse"];
export type MeUpdate = components["schemas"]["MeUpdate"];

export const ME_KEY = ["me"] as const;

export function useMe() {
  return useQuery({
    queryKey: ME_KEY,
    queryFn: () => api.get<Me>("/v1/me"),
    staleTime: 60_000,
    retry: false,
  });
}

export function useUpdateMe() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: MeUpdate) => api.patch<Me>("/v1/me", body),
    onSuccess: (me) => {
      qc.setQueryData(ME_KEY, me);
    },
  });
}

/**
 * Persist the user's default rest preference (06 §4). The active session resolves
 * its rest value against this default; "Save as my default" on the rest bar calls
 * this. Thin wrapper over the /v1/me PATCH so the rest bar reads cleanly.
 */
export function useUpdateDefaultRest() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (seconds: number) =>
      api.patch<Me>("/v1/me", { default_rest_seconds: seconds }),
    onSuccess: (me) => {
      qc.setQueryData(ME_KEY, me);
    },
  });
}
