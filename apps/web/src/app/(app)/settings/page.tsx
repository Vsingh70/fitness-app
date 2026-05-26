"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { api } from "@/lib/api/client";
import type { ApiError } from "@/lib/api/client";

interface MeResponse {
  id: string;
  email: string | null;
  display_name: string | null;
  unit_system: "metric" | "imperial";
  timezone: string;
}

export default function SettingsPage() {
  const router = useRouter();
  const qc = useQueryClient();

  const meQuery = useQuery({
    queryKey: ["me"],
    queryFn: () => api.get<MeResponse>("/v1/me"),
    retry: false,
  });

  const signOut = useMutation({
    mutationFn: async () => {
      await fetch("/api/auth/logout", { method: "POST", credentials: "include" });
    },
    onSuccess: () => {
      qc.clear();
      router.push("/sign-in");
    },
  });

  if (meQuery.isLoading) {
    return <div className="text-text-secondary">Loading...</div>;
  }

  if (meQuery.isError) {
    const err = meQuery.error as unknown as ApiError;
    if (err?.status === 401) {
      router.push("/sign-in");
      return null;
    }
    return <div className="text-destructive">Failed to load profile: {err?.message}</div>;
  }

  const me = meQuery.data;

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-6">
      <h1 className="text-3xl font-semibold tracking-tight">Settings</h1>

      <Card>
        <CardHeader>
          <h2 className="text-lg font-semibold">Account</h2>
        </CardHeader>
        <CardContent className="flex flex-col gap-2">
          <div>
            <span className="text-text-secondary text-sm">Email</span>
            <p>{me?.email ?? "Hidden"}</p>
          </div>
          <div>
            <span className="text-text-secondary text-sm">Display name</span>
            <p>{me?.display_name ?? "Not set"}</p>
          </div>
          <div>
            <span className="text-text-secondary text-sm">Units</span>
            <p>{me?.unit_system}</p>
          </div>
          <div>
            <span className="text-text-secondary text-sm">Time zone</span>
            <p>{me?.timezone}</p>
          </div>
        </CardContent>
      </Card>

      <Button variant="destructive" onClick={() => signOut.mutate()} disabled={signOut.isPending}>
        {signOut.isPending ? "Signing out..." : "Sign out"}
      </Button>
    </div>
  );
}
