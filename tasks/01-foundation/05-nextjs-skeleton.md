# 01.05 Next.js web skeleton

## Context

The web app is one of two clients. Same data, iOS-native visual language.

Reference: `00-overview/api-conventions.md`, `00-overview/design-system.md`.

## Goal

A Next.js 15 app with auth flow, typed API client, and the shell layout. No domain features yet beyond what's needed to prove the loop works.

## Stack

- Next.js 15 (App Router, React 19)
- TypeScript strict
- Tailwind CSS v4 with custom tokens that mirror iOS semantic colors
- Tanstack Query for server state, Zustand for UI state
- Zod for runtime validation
- `openapi-typescript` to generate `lib/api/types.ts` from `/openapi.json`
- Google Identity Services and Apple JS for sign-in

## Layout

```
apps/web/
  src/
    app/
      (auth)/
        sign-in/page.tsx
        callback/page.tsx
      (app)/
        layout.tsx               # shell with sidebar/tab bar
        page.tsx                 # today / home
        workouts/
        programs/
        nutrition/
        analytics/
        settings/
      api/                       # only used for OAuth callback if needed
      layout.tsx
      globals.css
    components/
      ui/                        # Card, StatTile, Sheet, Toast, etc.
      auth/
      layout/
    lib/
      api/
        client.ts                # fetch wrapper with auth + refresh
        types.ts                 # generated
      auth/
      hooks/
    styles/
      tokens.css
  public/
  package.json
  tsconfig.json
  tailwind.config.ts
  .env.example
```

## Deliverables

1. App scaffold with App Router and the routes above (most as empty placeholder pages).
2. Tailwind v4 config with the design system tokens. Light + dark modes via `prefers-color-scheme` + manual toggle in settings.
3. Typed API client:
   - `lib/api/client.ts` exposes `api.get`, `api.post`, etc.
   - Reads access token from `httpOnly` cookie (set by an internal `/api/session` route that proxies refresh).
   - Auto-refreshes on 401 once.
4. Sign-in page with Apple JS and Google Identity Services buttons. Exchange ID token against `/v1/auth/apple` or `/v1/auth/google`. Store tokens in httpOnly cookies (access in a 15min cookie, refresh in a 60-day cookie, both `Secure`, `SameSite=Lax`).
5. Shell layout for authenticated routes:
   - Mobile: bottom tab bar with Today, Workouts, Programs, Nutrition, Insights.
   - Desktop: left sidebar with the same items + Settings.
   - Top bar with workout-in-progress indicator slot (filled by later tasks).
6. UI primitives: `Card`, `StatTile`, `Sheet`, `Toast`, `Button`, `Input`. Match design system spec.
7. `/me` page that shows the logged-in user and a sign-out button.
8. ESLint + Prettier + a `npm run typecheck` script in CI.

## Acceptance criteria

- Apple and Google sign-in flows work end to end against the dev API.
- Refresh-on-401 works.
- The shell renders identically in light and dark with no contrast bugs.
- `npm run build` produces a clean prod build.

## Dependencies

- `01.02 FastAPI skeleton`
- `01.03 Auth`

## Out of scope

- Any domain pages (those are stubbed and filled in by 02+).
- Push notifications / web push (later).
