# Programs iOS — Phase 2 (live data layer + auth + wiring)

> Builds the from-scratch iOS networking + auth + Codable layer and wires the Programs feature
> (Phase-1 UI) to the live backend. Built by the loop: Builder = `ios-dev`, Checker = `qa-verifier`
> (gate = `xcodebuild ... build` succeeds). Live-verified by the orchestrator against the running
> dev API (simulator → `http://localhost:8000`).

**Context:** iOS is currently 100% mock (`ProgramsStore` mutates `MockData`). No API client, no auth,
no Codable. Phase 1 reshaped the models + screens to the new microcycle/mesocycle shape; this phase
makes them run on real data. The dev API is running locally at `http://127.0.0.1:8000` (env `dev`,
so `POST /v1/auth/dev` works) and the DB is at migration `0027`.

**Architecture decisions (locked for this phase):**
- **Base URL** via a `Config` struct, default `http://localhost:8000` (the simulator reaches the host
  loopback). Add an **ATS exception** for localhost in DEBUG (Info.plist `NSAppTransportSecurity` →
  `NSAllowsLocalNetworking` true) so plain-HTTP localhost works in the simulator.
- **Auth (dev path only this phase):** `POST /v1/auth/dev {sub,email}` → tokens; store the access +
  refresh tokens in the **Keychain**; send `Authorization: Bearer <access>`. On launch in **DEBUG**,
  auto dev-sign-in with a stable sub (`ios-dev-user`) if no token is stored. **Production sign-in
  (Apple/Google) is explicitly OUT of scope** — a separate feature; leave a clear seam for it.
- **Models:** new `Codable` API structs mirror the backend exactly; the Builder MUST ground them in a
  live response (the API is up). Map API structs → the existing Phase-1 view structs in `MockData.swift`
  so the **views do not change** (only their data source does).
- **Async/await + @Observable** store; loading/error states surfaced in the spine/root.

**Build gate (Checker):**
`xcodebuild -project apps/ios/GymApp.xcodeproj -scheme GymApp -configuration Debug -destination 'platform=iOS Simulator,name=iPhone 17 Pro' -quiet CODE_SIGNING_ALLOWED=NO build` → `** BUILD SUCCEEDED **`.

---

## Task A — networking + auth foundation (compiles)

**Files (new):** `Core/Networking/Config.swift`, `Core/Networking/APIClient.swift`,
`Core/Networking/APIModels.swift`, `Core/Auth/Keychain.swift`, `Core/Auth/TokenStore.swift`,
`Core/Auth/AuthService.swift`. **Modify:** the app target Info.plist (ATS) — find how Info is
configured (the project may use GENERATE_INFOPLIST_FILE; if so add `INFOPLIST_KEY_...` or a custom
plist with the ATS exception).

**Ground the models in reality first.** With the API running, the Builder should:
```bash
TOK=$(curl -s -X POST http://127.0.0.1:8000/v1/auth/dev -H 'content-type: application/json' \
  -d '{"sub":"ios-dev-user","email":"ios-dev-user@example.com"}' | python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')
curl -s http://127.0.0.1:8000/v1/programs -H "authorization: Bearer $TOK" | python3 -m json.tool | head -60
curl -s http://127.0.0.1:8000/v1/program-templates -H "authorization: Bearer $TOK" | python3 -m json.tool | head -40
```
Build `Codable` structs to match the **exact** JSON (note the response envelope from
`tasks/00-overview/api-conventions.md` — confirm whether lists wrap in `{items, next_cursor}` and
whether there's a top-level `data` envelope; match it). Use `keyDecodingStrategy = .convertFromSnakeCase`
or explicit `CodingKeys`. Cover: `APIProgram`, `APIProgramSlot` (day), `APIProgramExercise`,
`APIProgramListItem` (+ `APIProgramList`), `APIPosition`, `APITemplateSummary`.

- `APIClient`: async `request<T: Decodable>(_ method, _ path, body:, auth: Bool) throws -> T`,
  base URL from `Config`, bearer header from `TokenStore`, JSON encode/decode, an `APIError` enum
  (network / decoding / status>=400 with server message). A 401 path can attempt one refresh via
  `POST /v1/auth/refresh` (if that endpoint exists — check; otherwise re-dev-sign-in in DEBUG).
- `Keychain`: minimal generic-password get/set/delete wrapper.
- `TokenStore`: `@Observable`/actor holding access+refresh, persisted in Keychain.
- `AuthService`: `devSignIn(sub:)` calling `/v1/auth/dev`, storing tokens; `currentToken`; in DEBUG a
  `ensureSignedIn()` that dev-signs-in if no token.
- **DoD:** `xcodebuild ... build` = BUILD SUCCEEDED.

## Task B — wire ProgramsStore to the live API (compiles)

**Files:** `Features/Programs/ProgramsStore.swift` (rewrite to async API-backed), small loading/error
UI in `ProgramsRootView.swift` / `ProgramsHomeView.swift`, and the app entry
(`App/GymAppApp.swift` / `AppRoot.swift`) to inject `APIClient`/`AuthService` and kick the initial
load. Keep `MockData` view structs as the view-facing shape; add a mapping `APIProgram → Program`,
`APIProgramSlot → ProgramDay`, etc.

- On launch (DEBUG): `AuthService.ensureSignedIn()` then `store.load()`.
- `ProgramsStore` async methods backed by the client: `load()` (GET /v1/programs → map),
  `position(for:)` (GET /v1/programs/{id}/position), `activate/deactivate`, `addSlot/deleteSlot/
  reorderSlots/toggleRest`, `addExercise`, `duplicate`, `saveAsTemplate`, `copyTemplate(slug)`,
  `createEmpty`, `templates()` (GET /v1/program-templates). Replace all `MockData.myPrograms`/
  `MockData.templates` reads in the Programs views' data path with store calls.
- Loading + error states: a quiet spinner/skeleton while loading; an inline error with retry on failure
  (honor the editorial language; reuse Core/Design). Never crash on a decode/network error.
- Keep the screens otherwise unchanged from Phase 1.
- **DoD:** `xcodebuild ... build` = BUILD SUCCEEDED.

## Live verification (orchestrator, not the loop)
With the dev API running and a seeded program (reuse `apps/web/scripts/programs-shots.mjs` seeding or
seed via curl as the same `ios-dev-user`), boot iPhone 17 Pro, install + launch the built app, and
confirm the spine/library render **real** server data (not MockData) — screenshot light + dark.
Then shut the dev servers down.

## Out of scope
- Production Apple/Google sign-in UI + token refresh hardening (separate feature; DEBUG dev-sign-in
  seam is in place).
- Offline cache / optimistic mutations (server round-trip is fine for now).
- Other iOS surfaces (Today/Workouts/etc.) — they stay mock until their own ports.
