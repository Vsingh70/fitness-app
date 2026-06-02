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
