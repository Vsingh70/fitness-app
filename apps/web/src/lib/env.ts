/**
 * Server-only env helpers. Throws at runtime if a required var is missing in prod.
 * Public NEXT_PUBLIC_* values can be read directly via process.env on the client.
 */

export function serverEnv() {
  const backendUrl = process.env.BACKEND_INTERNAL_URL ?? "http://localhost:8000";
  const cookieSecure = process.env.COOKIE_SECURE === "true";
  const cookieDomain = process.env.COOKIE_DOMAIN || undefined;
  return { backendUrl, cookieSecure, cookieDomain };
}

export function publicAuthConfig() {
  return {
    googleClientId: process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID ?? "",
    appleServiceId: process.env.NEXT_PUBLIC_APPLE_SERVICE_ID ?? "",
    appleRedirectUri: process.env.NEXT_PUBLIC_APPLE_REDIRECT_URI ?? "",
  };
}
