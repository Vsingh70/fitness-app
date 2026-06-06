import { Suspense } from "react";

import { SignInButtons } from "@/components/auth/sign-in-buttons";
import { publicAuthConfig } from "@/lib/env";

export default function SignInPage() {
  const config = publicAuthConfig();
  return (
    <div className="bg-bg flex min-h-screen items-center justify-center px-6 py-8">
      <div className="flex w-full max-w-[380px] flex-col items-center">
        <span
          className="bg-accent text-accent-foreground mb-6 grid h-16 w-16 place-items-center rounded-[12px] font-serif text-3xl font-semibold tracking-tight"
          aria-hidden
        >
          V
        </span>
        <h1 className="font-serif text-[28px] font-medium tracking-tight">Welcome to VGains</h1>
        <p className="text-text-secondary mt-1.5 mb-8 text-center text-sm leading-snug">
          One account across web and iOS. Apple and Google only — no passwords to forget.
        </p>
        <Suspense fallback={<div className="h-[50px] w-full max-w-[280px]" aria-hidden />}>
          <SignInButtons
            googleClientId={config.googleClientId}
            appleServiceId={config.appleServiceId}
            appleRedirectUri={config.appleRedirectUri}
          />
        </Suspense>
        <p className="text-text-tertiary mt-6 max-w-[300px] text-center text-xs leading-relaxed">
          By continuing, you agree to the Terms and Privacy. We don&apos;t share your data, ever.
        </p>
      </div>
    </div>
  );
}
