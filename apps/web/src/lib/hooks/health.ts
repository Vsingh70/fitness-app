"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import * as health from "@/lib/api/health";
import { generatePkce } from "@/lib/hooks/fitbit";

const STATUS_KEY = ["health", "status"] as const;

/** localStorage key for the PKCE verifier, read back on the callback page. */
export const HEALTH_VERIFIER_KEY = "om.health.verifier";

export function useHealthStatus() {
  return useQuery({
    queryKey: STATUS_KEY,
    queryFn: health.getHealthStatus,
    staleTime: 30_000,
    retry: false,
  });
}

/** Starts the OAuth flow: generates PKCE, stores the verifier, redirects to Google. */
export function useConnectHealth() {
  return useMutation({
    mutationFn: async () => {
      const { verifier, challenge } = await generatePkce();
      window.localStorage.setItem(HEALTH_VERIFIER_KEY, verifier);
      const { authorize_url } = await health.authorizeHealth(challenge);
      window.location.assign(authorize_url);
    },
  });
}

export function useDisconnectHealth() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: health.disconnectHealth,
    onSuccess: () => {
      qc.setQueryData(STATUS_KEY, { connected: false });
      qc.invalidateQueries({ queryKey: STATUS_KEY });
    },
  });
}

export function useCompleteHealthCallback() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (args: { code: string; state: string; code_verifier: string }) =>
      health.callbackHealth(args),
    onSuccess: (status) => {
      qc.setQueryData(STATUS_KEY, status);
      qc.invalidateQueries({ queryKey: STATUS_KEY });
    },
  });
}

/** Pull the latest weight + body-fat readings from the connected account. */
export function useSyncHealth() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: health.syncHealth,
    onSuccess: () => {
      // Refresh last_synced_at and any weight/body-metric history views.
      qc.invalidateQueries({ queryKey: STATUS_KEY });
      qc.invalidateQueries({ queryKey: ["body-metrics"] });
    },
  });
}

/** TEMPORARY (spike): discover daily-metric dataType IDs + shapes. */
export function useProbeHealth() {
  return useMutation({ mutationFn: health.probeHealth });
}
