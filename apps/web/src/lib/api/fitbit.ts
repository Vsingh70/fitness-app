"use client";

import { api } from "@/lib/api/client";
import type { components } from "@/lib/api/types";

export type FitbitStatus = components["schemas"]["FitbitStatusResponse"];
export type FitbitSyncResult = components["schemas"]["FitbitSyncResponse"];
export type FitbitAuthorizeResponse = components["schemas"]["FitbitAuthorizeResponse"];

export const getFitbitStatus = () => api.get<FitbitStatus>("/v1/integrations/fitbit/status");

export const authorizeFitbit = (codeChallenge: string) =>
  api.post<FitbitAuthorizeResponse>("/v1/integrations/fitbit/authorize", {
    code_challenge: codeChallenge,
  });

export const callbackFitbit = (args: { code: string; state: string; code_verifier: string }) =>
  api.post<FitbitStatus>("/v1/integrations/fitbit/callback", args);

export const disconnectFitbit = () => api.delete<void>("/v1/integrations/fitbit");

export const syncFitbit = () => api.post<FitbitSyncResult>("/v1/integrations/fitbit/sync");
