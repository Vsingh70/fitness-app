/**
 * OAuth callback landing page.
 *
 * Apple's popup-mode flow returns directly to the opener window. Form-post mode
 * (used in some browsers) lands on this redirect_uri. For now this page just
 * confirms receipt; the actual token exchange happens client-side on /sign-in
 * via the SDK callback.
 */
export default function AuthCallbackPage() {
  return (
    <div className="flex min-h-screen items-center justify-center px-4">
      <p className="text-text-secondary">Completing sign-in...</p>
    </div>
  );
}
