import { SignInButtons } from "@/components/auth/sign-in-buttons";
import { publicAuthConfig } from "@/lib/env";

export default function SignInPage() {
  const config = publicAuthConfig();
  return (
    <div className="bg-bg flex min-h-screen items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <header className="mb-6 text-center">
          <h1 className="text-3xl font-semibold tracking-tight">Sign in</h1>
          <p className="text-text-secondary mt-1 text-sm">Use Apple or Google to get started.</p>
        </header>
        <SignInButtons
          googleClientId={config.googleClientId}
          appleServiceId={config.appleServiceId}
          appleRedirectUri={config.appleRedirectUri}
        />
      </div>
    </div>
  );
}
