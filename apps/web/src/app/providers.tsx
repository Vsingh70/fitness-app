"use client";

import { MutationCache, QueryCache, QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";

import { handleApiAuthError } from "@/lib/api/on-auth-error";

export function Providers({ children }: { children: ReactNode }) {
  const [client] = useState(
    () =>
      new QueryClient({
        // A 401 means the session is dead; redirect to sign-in consistently for every
        // query/mutation instead of leaving pages stranded on an inline error.
        queryCache: new QueryCache({ onError: handleApiAuthError }),
        mutationCache: new MutationCache({ onError: handleApiAuthError }),
        defaultOptions: {
          queries: {
            staleTime: 30_000,
            retry: 1,
            refetchOnWindowFocus: false,
          },
        },
      }),
  );

  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}
