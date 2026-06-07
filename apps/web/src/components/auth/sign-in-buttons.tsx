"use client";

import { useEffect, useRef, useState } from "react";
import Script from "next/script";
import { useRouter, useSearchParams } from "next/navigation";

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
  const searchParams = useSearchParams();
  // Return the user to where the middleware intercepted them, defaulting home.
  // Only allow internal paths to avoid an open-redirect.
  const nextParam = searchParams.get("next");
  const redirectTo = nextParam && nextParam.startsWith("/") ? nextParam : "/";
  // Wraps the visible (styled) button; the real GIS button is overlaid on top
  // of it transparently, so we measure this to size GIS's button to match.
  const googleWrapRef = useRef<HTMLDivElement>(null);
  const googleButtonRef = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  // Flips true once the Google Identity Services script has loaded. Without this
  // the render effect runs before window.google exists and bails out forever,
  // leaving the button container empty (the GIS-in-React race condition).
  const [googleReady, setGoogleReady] = useState(false);
  // Pixel width handed to GIS renderButton (it needs an explicit px width and
  // won't render into a zero-size container). Measured from the visible button.
  const [googleWidth, setGoogleWidth] = useState(0);

  const hasGoogle = googleClientId.length > 0;
  const hasApple = appleServiceId.length > 0 && appleRedirectUri.length > 0;

  // Measure the visible button so GIS renders its (transparent) real button at
  // the same width. GIS requires an explicit px width and a non-zero container.
  useEffect(() => {
    if (!hasGoogle) return;
    const el = googleWrapRef.current;
    if (!el) return;
    const measure = () => setGoogleWidth(Math.round(el.getBoundingClientRect().width));
    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(el);
    return () => ro.disconnect();
  }, [hasGoogle]);

  useEffect(() => {
    if (!hasGoogle || !googleReady || !googleButtonRef.current || googleWidth === 0) return;
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
          router.replace(redirectTo);
        } catch (e) {
          setError(e instanceof Error ? e.message : "Sign-in failed");
        } finally {
          setBusy(false);
        }
      },
    });
    // Render Google's REAL button transparently on top of our editorial-styled
    // button (the overlay below). The user clicks Google's genuine button — a
    // real user gesture Google accepts — but sees our design. We deliberately
    // avoid programmatically .click()-ing a hidden button: GIS won't reliably
    // render into a zero-size container and increasingly blocks synthetic
    // clicks, which left the button doing nothing ("isn't ready yet").
    googleButtonRef.current.innerHTML = "";
    win.google.accounts.id.renderButton(googleButtonRef.current, {
      theme: "outline",
      size: "large",
      width: googleWidth,
    });
  }, [hasGoogle, googleReady, googleWidth, googleClientId, router, redirectTo]);

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
      router.replace(redirectTo);
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
        <code className="bg-surface rounded px-1 font-mono text-xs">
          NEXT_PUBLIC_GOOGLE_CLIENT_ID
        </code>{" "}
        or{" "}
        <code className="bg-surface rounded px-1 font-mono text-xs">
          NEXT_PUBLIC_APPLE_SERVICE_ID
        </code>{" "}
        in <code className="bg-surface rounded px-1 font-mono text-xs">apps/web/.env.local</code>.
      </p>
    );
  }

  return (
    <div className="relative flex w-full flex-col items-stretch gap-2">
      {hasApple ? (
        <>
          <Script
            src="https://appleid.cdn-apple.com/appleauth/static/jsapi/appleid/1/en_US/appleid.auth.js"
            strategy="afterInteractive"
          />
          <button
            type="button"
            disabled={busy}
            onClick={onAppleClick}
            className="bg-text text-bg dark:bg-text dark:text-bg inline-flex h-[50px] items-center justify-center gap-2.5 rounded-[var(--radius-button)] text-[15px] font-semibold disabled:cursor-not-allowed disabled:opacity-60"
          >
            Continue with Apple
          </button>
        </>
      ) : null}
      {hasGoogle ? (
        <>
          <Script
            src="https://accounts.google.com/gsi/client"
            strategy="afterInteractive"
            onLoad={() => setGoogleReady(true)}
            onReady={() => setGoogleReady(true)}
          />
          {/* Our editorial-styled button is the VISIBLE layer; Google's real
              button is rendered transparently on top of it and receives the
              click (a genuine user gesture Google accepts). */}
          <div ref={googleWrapRef} className="relative h-[50px] w-full">
            <div
              aria-hidden
              className="border-border-strong bg-surface-elevated text-text pointer-events-none absolute inset-0 flex items-center justify-center gap-2.5 rounded-[var(--radius-button)] border text-[15px] font-semibold"
            >
              <GoogleGlyph />
              Continue with Google
            </div>
            {/* Transparent real GIS button overlay. opacity-0 keeps it clickable
                (unlike display:none / zero-size, which GIS refuses to render). */}
            <div
              ref={googleButtonRef}
              className="absolute inset-0 flex items-center justify-center [color-scheme:light] opacity-0"
              style={{ visibility: googleReady && googleWidth > 0 ? "visible" : "hidden" }}
            />
            {busy ? (
              <div className="bg-surface-elevated/60 absolute inset-0 grid place-items-center rounded-[var(--radius-button)]">
                <span className="text-text-secondary text-sm">Signing in…</span>
              </div>
            ) : null}
          </div>
        </>
      ) : null}
      {error ? <p className="text-destructive text-sm">{error}</p> : null}
    </div>
  );
}

/** Google's four-color "G" mark (keeps brand colors per Google's button guidelines). */
function GoogleGlyph() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" aria-hidden focusable="false">
      <path
        fill="#4285F4"
        d="M17.64 9.2c0-.64-.06-1.25-.16-1.84H9v3.48h4.84a4.14 4.14 0 0 1-1.8 2.72v2.26h2.92c1.7-1.57 2.68-3.88 2.68-6.62Z"
      />
      <path
        fill="#34A853"
        d="M9 18c2.43 0 4.47-.8 5.96-2.18l-2.92-2.26c-.81.54-1.84.86-3.04.86-2.34 0-4.32-1.58-5.03-3.7H.96v2.33A9 9 0 0 0 9 18Z"
      />
      <path
        fill="#FBBC05"
        d="M3.97 10.72A5.41 5.41 0 0 1 3.68 9c0-.6.1-1.18.29-1.72V4.95H.96A9 9 0 0 0 0 9c0 1.45.35 2.83.96 4.05l3.01-2.33Z"
      />
      <path
        fill="#EA4335"
        d="M9 3.58c1.32 0 2.5.45 3.44 1.35l2.58-2.58C13.46.89 11.43 0 9 0A9 9 0 0 0 .96 4.95l3.01 2.33C4.68 5.16 6.66 3.58 9 3.58Z"
      />
    </svg>
  );
}
