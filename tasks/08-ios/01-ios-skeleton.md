# 08.01 iOS app skeleton

## Context

Swift + SwiftUI native iOS app. Same API as the web. Reference: `00-overview/design-system.md`.

## Goal

A buildable iOS app with auth flow, shared design tokens, generated API client, and the tab bar shell.

## Stack

- Xcode 16+, iOS 17+ minimum.
- Swift 6, strict concurrency.
- SwiftUI primary. UIKit only for things SwiftUI can't do cleanly (e.g. swipe actions in some lists if needed).
- `swift-openapi-generator` for the API client (generated from `packages/openapi/openapi.json`).
- `swift-openapi-urlsession` transport.
- KeychainAccess (or our own thin wrapper) for token storage.
- Apple Sign-In via AuthenticationServices.
- Google Sign-In via GoogleSignIn-iOS SDK.

## Project layout

```
apps/ios/
  GymApp.xcodeproj
  GymApp/
    App/
      GymAppApp.swift           # @main
      AppRoot.swift             # root view: AuthGate -> MainTabs
    Auth/
      AuthService.swift
      SignInView.swift
      AppleSignInButton.swift
      GoogleSignInButton.swift
    Core/
      API/
        Generated/               # swift-openapi-generator output
        APIClient.swift          # auth + refresh wrapper
        Idempotency.swift
      Storage/
        KeychainStore.swift
        UserDefaultsStore.swift
      Design/
        Colors.swift              # semantic colors from xcassets
        Typography.swift
        Components/
          AppCard.swift
          StatTile.swift
          RestTimerView.swift
          SetRow.swift
          ExercisePickerSheet.swift
      Utilities/
        Logger.swift
        Telemetry.swift
    Features/                     # filled in by later 08-ios tasks
      Today/
      Workouts/
      Programs/
      Nutrition/
      Insights/
      Settings/
    Resources/
      Assets.xcassets
      Localizable.strings
  GymAppTests/
  GymAppUITests/
```

## Deliverables

1. Xcode project with the layout above.
2. Generated OpenAPI client wired into `APIClient`.
3. Auth flow:
   - Apple sign-in via `SignInWithAppleButton`.
   - Google sign-in via the official SDK.
   - On success, post the identity token to our API, store the access + refresh tokens in Keychain.
   - Auto-refresh on 401 with rotation.
4. App root: if auth tokens are present and valid, show the main tab bar; else show sign-in.
5. Tab bar with 5 tabs (Today, Workouts, Programs, Nutrition, Insights). Empty placeholder views.
6. Design system: semantic colors in xcassets, typography helper, four core components (`AppCard`, `StatTile`, `SetRow`, `RestTimerView`) implemented and previewed.
7. Settings entry with Sign Out, unit system toggle, accent color picker (matches web).
8. Tests:
   - APIClient handles 401 -> refresh once -> retry.
   - Snapshot tests on the four core components in light + dark.

## Acceptance criteria

- App builds clean in debug + release.
- Sign-in with both providers works against the dev API.
- App handles refresh seamlessly: simulate access token expiry, verify a single 401 leads to a refresh + retry.
- All components render correctly in light and dark.

## Dependencies

- `01.02 FastAPI skeleton`
- `01.03 Auth`

## Out of scope

- Domain features (later 08.xx tasks).
