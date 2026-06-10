"use client";

import { api } from "@/lib/api/client";
import type { components } from "@/lib/api/types";

export type HealthStatus = components["schemas"]["HealthStatusResponse"];
export type HealthAuthorizeResponse = components["schemas"]["HealthAuthorizeResponse"];
export type HealthSyncResponse = components["schemas"]["HealthSyncResponse"];

export const getHealthStatus = () => api.get<HealthStatus>("/v1/integrations/health/status");

export const authorizeHealth = (codeChallenge: string) =>
  api.post<HealthAuthorizeResponse>("/v1/integrations/health/authorize", {
    code_challenge: codeChallenge,
  });

export const callbackHealth = (args: { code: string; state: string; code_verifier: string }) =>
  api.post<HealthStatus>("/v1/integrations/health/callback", args);

export const disconnectHealth = () => api.delete<void>("/v1/integrations/health");

/** Pull weight + body-fat from the connected account into the weight history. */
export const syncHealth = () => api.post<HealthSyncResponse>("/v1/integrations/health/sync");
