"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import * as fitbit from "@/lib/api/fitbit";

const STATUS_KEY = ["fitbit", "status"] as const;

/** localStorage key for the PKCE verifier, read back on the callback page. */
export const FITBIT_VERIFIER_KEY = "om.fitbit.verifier";

function base64url(bytes: Uint8Array): string {
  let str = "";
  for (const b of bytes) str += String.fromCharCode(b);
  return btoa(str).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

/** Generate a PKCE code verifier (43-128 chars) and its S256 challenge. */
export async function generatePkce(): Promise<{ verifier: string; challenge: string }> {
  const random = new Uint8Array(32);
  crypto.getRandomValues(random);
  const verifier = base64url(random);
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(verifier));
  const challenge = base64url(new Uint8Array(digest));
  return { verifier, challenge };
}

export function useFitbitStatus() {
  return useQuery({
    queryKey: STATUS_KEY,
    queryFn: fitbit.getFitbitStatus,
    staleTime: 30_000,
    retry: false,
  });
}

/** Starts the OAuth flow: generates PKCE, stores the verifier, redirects to Fitbit. */
export function useConnectFitbit() {
  return useMutation({
    mutationFn: async () => {
      const { verifier, challenge } = await generatePkce();
      window.localStorage.setItem(FITBIT_VERIFIER_KEY, verifier);
      const { authorize_url } = await fitbit.authorizeFitbit(challenge);
      window.location.assign(authorize_url);
    },
  });
}

export function useDisconnectFitbit() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: fitbit.disconnectFitbit,
    onSuccess: () => {
      qc.setQueryData(STATUS_KEY, { connected: false, scopes: [] });
      qc.invalidateQueries({ queryKey: STATUS_KEY });
    },
  });
}

export function useSyncFitbit() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: fitbit.syncFitbit,
    onSuccess: () => qc.invalidateQueries({ queryKey: STATUS_KEY }),
  });
}

export function useCompleteFitbitCallback() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (args: { code: string; state: string; code_verifier: string }) =>
      fitbit.callbackFitbit(args),
    onSuccess: (status) => {
      qc.setQueryData(STATUS_KEY, status);
      qc.invalidateQueries({ queryKey: STATUS_KEY });
    },
  });
}
