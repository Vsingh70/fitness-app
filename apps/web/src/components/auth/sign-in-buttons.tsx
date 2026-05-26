"use client";

import { useEffect, useRef, useState } from "react";
import Script from "next/script";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";

interface SignInButtonsProps {
  googleClientId: string;
  appleServiceId: string;
  appleRedirectUri: string;
}

interface GoogleCredentialResponse {
  credential: string;
}

interface GoogleApi {
  accounts: {
    id: {
      initialize: (config: {
        client_id: string;
        callback: (response: GoogleCredentialResponse) => void;
      }) => void;
      renderButton: (
        parent: HTMLElement,
        options: { theme?: string; size?: string; width?: number },
      ) => void;
    };
  };
}

interface AppleApi {
  auth: {
    init: (config: {
      clientId: string;
      scope: string;
      redirectURI: string;
      usePopup: boolean;
    }) => void;
    signIn: () => Promise<{ authorization?: { id_token?: string } }>;
  };
}

declare global {
  interface Window {
    google?: GoogleApi;
    AppleID?: AppleApi;
  }
}

export function SignInButtons({
  googleClientId,
  appleServiceId,
  appleRedirectUri,
}: SignInButtonsProps) {
  const router = useRouter();
  const googleButtonRef = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const hasGoogle = googleClientId.length > 0;
  const hasApple = appleServiceId.length > 0 && appleRedirectUri.length > 0;

  useEffect(() => {
    if (!hasGoogle || !googleButtonRef.current) return;
    const win = window;
    if (!win.google) return;
    win.google.accounts.id.initialize({
      client_id: googleClientId,
      callback: async (resp) => {
        setBusy(true);
        try {
          const result = await fetch("/api/auth/google", {
            method: "POST",
            credentials: "include",
            headers: { "content-type": "application/json" },
            body: JSON.stringify({ id_token: resp.credential }),
          });
          if (!result.ok) {
            throw new Error("Sign-in failed");
          }
          router.replace("/");
        } catch (e) {
          setError(e instanceof Error ? e.message : "Sign-in failed");
        } finally {
          setBusy(false);
        }
      },
    });
    win.google.accounts.id.renderButton(googleButtonRef.current, {
      theme: "outline",
      size: "large",
      width: 280,
    });
  }, [hasGoogle, googleClientId, router]);

  const onAppleClick = async () => {
    if (!hasApple || !window.AppleID) return;
    setBusy(true);
    setError(null);
    try {
      window.AppleID.auth.init({
        clientId: appleServiceId,
        scope: "name email",
        redirectURI: appleRedirectUri,
        usePopup: true,
      });
      const data = await window.AppleID.auth.signIn();
      const idToken = data.authorization?.id_token;
      if (!idToken) throw new Error("Apple returned no id_token");
      const result = await fetch("/api/auth/apple", {
        method: "POST",
        credentials: "include",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ id_token: idToken }),
      });
      if (!result.ok) throw new Error("Sign-in failed");
      router.replace("/");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Sign-in failed");
    } finally {
      setBusy(false);
    }
  };

  if (!hasGoogle && !hasApple) {
    return (
      <p className="text-text-secondary text-sm">
        Sign-in is not configured for this environment. Set{" "}
        <code className="bg-surface rounded px-1">NEXT_PUBLIC_GOOGLE_CLIENT_ID</code> or{" "}
        <code className="bg-surface rounded px-1">NEXT_PUBLIC_APPLE_SERVICE_ID</code> in{" "}
        <code className="bg-surface rounded px-1">apps/web/.env.local</code>.
      </p>
    );
  }

  return (
    <div className="flex flex-col items-stretch gap-3">
      {hasGoogle ? (
        <>
          <Script src="https://accounts.google.com/gsi/client" strategy="afterInteractive" />
          <div ref={googleButtonRef} />
        </>
      ) : null}
      {hasApple ? (
        <>
          <Script
            src="https://appleid.cdn-apple.com/appleauth/static/jsapi/appleid/1/en_US/appleid.auth.js"
            strategy="afterInteractive"
          />
          <Button variant="secondary" disabled={busy} onClick={onAppleClick}>
            Continue with Apple
          </Button>
        </>
      ) : null}
      {error ? <p className="text-destructive text-sm">{error}</p> : null}
    </div>
  );
}
