//
//  WorkoutsStore.swift
//  GymApp
//
//  Live, API-backed store for the Workouts feature. Drives two surfaces:
//
//  1. History — `GET /v1/workout-sessions` mapped into `MockData.Session` rows
//     for the Workouts tab list.
//  2. The active in-progress session — start from the active program's rotation
//     slot (`POST /v1/programs/{id}/start-session`), append sets
//     (`POST /v1/workout-exercises/{id}/sets`), edit/delete them
//     (`PATCH`/`DELETE /v1/sets/{id}`), run the rest timer locally, and finish
//     (`POST .../finish`) or skip (`POST .../skip`) — both advance the program
//     rotation server-side.
//
//  Design notes (mirrors `ProgramsStore`):
//  - Injected with an `APIClient` + `AuthService` (+ the shared `ProgramsStore`
//    to resolve the active program's server id and exercise names). When those
//    are nil (SwiftUI previews), the store stays offline and seeds from
//    `MockData` so the canvases still render.
//  - The active session is held as the raw `APISession` plus a derived
//    `MockData.ActiveSession`-shaped view model the screen reads unchanged.
//  - Mutations apply against the server, then re-fetch the session so set
//    indices / PR flags / denormalized values stay authoritative. Never crashes
//    on a network/decode error: failures land in `actionError`.
//

import SwiftUI

@MainActor
@Observable
final class WorkoutsStore {

    enum LoadState: Equatable {
        case idle, loading, loaded
        case failed(String)
    }

    // MARK: View-facing state

    /// History rows for the Workouts tab (newest-first).
    private(set) var sessions: [MockData.Session] = []
    private(set) var historyState: LoadState = .idle

    /// The live in-progress session, mapped into the screen's view model. Nil
    /// until a session is started/loaded.
    private(set) var active: ActiveView?
    /// The raw active session id (for finish/skip/add-set routing).
    private(set) var activeSessionID: String?

    /// True while a start/finish/skip POST is in flight.
    private(set) var isMutating = false
    /// A user-facing error from the last action (start/log/finish/skip).
    var actionError: String?

    /// Index of the currently-focused exercise in the active session's rail.
    var focusedExerciseIndex: Int = 0

    // MARK: Rest timer (local)

    /// Seconds elapsed in the current rest interval; nil when not resting.
    private(set) var restElapsedSeconds: Int?
    /// The target rest for the current interval (seconds).
    private(set) var restTotalSeconds: Int = 180
    /// The driving tick task; cancelled on stop/restart.
    private var restTask: Task<Void, Never>?

    // MARK: Dependencies

    private let client: APIClient?
    private let auth: AuthService?
    private let programsStore: ProgramsStore?

    /// id → exercise name lookup (best-effort), so logged exercises render a real
    /// label rather than a raw id.
    private var exerciseNames: [String: String] = [:]
    private var exerciseLibraryLoaded = false

    // MARK: Init

    /// Live init — used by the app shell.
    init(client: APIClient, auth: AuthService, programsStore: ProgramsStore) {
        self.client = client
        self.auth = auth
        self.programsStore = programsStore
    }

    /// Offline init — used by SwiftUI previews. Seeds from `MockData`.
    init(preview: Bool = true) {
        self.client = nil
        self.auth = nil
        self.programsStore = nil
        self.sessions = MockData.recentSessions
        self.active = Self.previewActive()
        self.activeSessionID = "preview"
        self.historyState = .loaded
    }

    // MARK: - History

    /// Fetch the session history and map into the Workouts-tab rows.
    func loadHistory() async {
        guard let client else { return }
        await auth?.ensureSignedIn()
        historyState = .loading
        do {
            await loadExerciseLibraryIfNeeded()
            let list: APIWorkoutSessionList = try await client.request(
                .get, "/workout-sessions?limit=30"
            )
            sessions = list.items.map(Self.mapHistoryRow)
            historyState = .loaded
        } catch {
            historyState = .failed(Self.message(for: error))
        }
    }

    // MARK: - Start

    /// Start a workout from the active program's current rotation slot
    /// (`POST /v1/programs/{id}/start-session`). On a rest-day (409) or no-slots
    /// (422) program slot, falls back to a freestyle session so the user can
    /// still log. Returns the new session id on success.
    @discardableResult
    func startSession() async -> String? {
        guard let client, let programsStore, let program = programsStore.active,
              let programID = programsStore.serverID(for: program) else { return nil }
        isMutating = true
        defer { isMutating = false }
        await loadExerciseLibraryIfNeeded()
        do {
            let session: APIWorkoutSession = try await client.request(
                .post, "/programs/\(programID)/start-session"
            )
            adopt(session)
            return session.id
        } catch {
            // Rest-day / no-slot → freestyle session so logging still works.
            if let api = error as? APIError, case let .server(status, _, _) = api,
               status == 409 || status == 422 {
                return await startFreestyle()
            }
            actionError = Self.message(for: error)
            return nil
        }
    }

    /// Create an empty session not tied to a slot.
    @discardableResult
    private func startFreestyle() async -> String? {
        guard let client else { return nil }
        do {
            struct Body: Encodable { let name: String? }
            let session: APIWorkoutSession = try await client.request(
                .post, "/workout-sessions", body: Body(name: nil)
            )
            adopt(session)
            return session.id
        } catch {
            actionError = Self.message(for: error)
            return nil
        }
    }

    /// Re-derive the active view model for the current `focusedExerciseIndex`
    /// (the rail taps this to switch the focused exercise without a fetch).
    func refocus() {
        guard let raw = rawSession else { return }
        active = mapActive(raw)
    }

    /// Load an existing session by id (re-entering an in-progress session).
    func openSession(id: String) async {
        guard let client else { return }
        await loadExerciseLibraryIfNeeded()
        do {
            let session: APIWorkoutSession = try await client.request(
                .get, "/workout-sessions/\(id)"
            )
            adopt(session)
        } catch {
            actionError = Self.message(for: error)
        }
    }

    // MARK: - Set logging

    /// Append a set to the focused exercise (`POST /workout-exercises/{id}/sets`),
    /// then re-fetch the session and start the rest timer. Decimals go over the
    /// wire as strings.
    func logSet(weightKg: Double?, reps: Int?, rpe: Double?) async {
        guard let client, let session = rawSession,
              let wex = focusedRawExercise(in: session) else { return }
        let body = APISetCreate(
            weightKg: weightKg.map(Self.decimalString),
            reps: reps,
            rpe: rpe.map(Self.decimalString),
            rir: nil,
            setType: "working"
        )
        do {
            _ = try await client.request(.post, "/workout-exercises/\(wex.id)/sets", body: body) as APIWorkoutSet
            await refreshActive()
            startRest(seconds: restTotalSeconds)
        } catch {
            actionError = Self.message(for: error)
        }
    }

    /// Edit a logged set (`PATCH /sets/{id}`) then re-fetch.
    func updateSet(setID: String, weightKg: Double?, reps: Int?, rpe: Double?) async {
        guard let client else { return }
        let body = APISetUpdate(
            weightKg: weightKg.map(Self.decimalString),
            reps: reps,
            rpe: rpe.map(Self.decimalString)
        )
        do {
            _ = try await client.request(.patch, "/sets/\(setID)", body: body) as APIWorkoutSet
            await refreshActive()
        } catch {
            actionError = Self.message(for: error)
        }
    }

    /// Delete a logged set (`DELETE /sets/{id}`) then re-fetch.
    func deleteSet(setID: String) async {
        guard let client else { return }
        do {
            try await client.requestVoid(.delete, "/sets/\(setID)")
            await refreshActive()
        } catch {
            actionError = Self.message(for: error)
        }
    }

    // MARK: - Finish / skip

    /// Finish the active session (`POST .../finish`). Advances the program
    /// rotation server-side. Refreshes history and clears the active session.
    func finish() async {
        guard let client, let id = activeSessionID else { return }
        isMutating = true
        defer { isMutating = false }
        do {
            _ = try await client.request(.post, "/workout-sessions/\(id)/finish") as APIWorkoutSession
            stopRest()
            clearActive()
            await loadHistory()
            await refreshPosition()
        } catch {
            actionError = Self.message(for: error)
        }
    }

    /// Skip the active session (`POST .../skip`). Keeps already-logged sets,
    /// advances the rotation neutrally.
    func skip() async {
        guard let client, let id = activeSessionID else { return }
        isMutating = true
        defer { isMutating = false }
        do {
            _ = try await client.request(.post, "/workout-sessions/\(id)/skip") as APIWorkoutSession
            stopRest()
            clearActive()
            await loadHistory()
            await refreshPosition()
        } catch {
            actionError = Self.message(for: error)
        }
    }

    // MARK: - Rest timer

    /// Start (or restart) the rest countdown for `seconds`. Driven by an async
    /// tick task on the main actor (no non-Sendable `Timer` captured).
    func startRest(seconds: Int) {
        restTotalSeconds = max(seconds, 1)
        restElapsedSeconds = 0
        restTask?.cancel()
        restTask = Task { [weak self] in
            while !Task.isCancelled {
                try? await Task.sleep(for: .seconds(1))
                if Task.isCancelled { return }
                guard let self, let e = self.restElapsedSeconds else { return }
                if e + 1 >= self.restTotalSeconds {
                    self.restElapsedSeconds = self.restTotalSeconds
                    self.restTask = nil
                    return
                }
                self.restElapsedSeconds = e + 1
            }
        }
    }

    func addRestTime(_ seconds: Int) {
        guard restElapsedSeconds != nil else { return }
        restTotalSeconds += seconds
    }

    func stopRest() {
        restTask?.cancel()
        restTask = nil
        restElapsedSeconds = nil
    }

    var isResting: Bool { restElapsedSeconds != nil }
    var restFraction: Double {
        guard let e = restElapsedSeconds, restTotalSeconds > 0 else { return 0 }
        return min(Double(e) / Double(restTotalSeconds), 1)
    }
    var restElapsedLabel: String { Self.clock(restElapsedSeconds ?? 0) }
    var restTotalLabel: String { Self.clock(restTotalSeconds) }

    // MARK: - Internals

    /// Raw active session kept alongside the derived view model.
    private var rawSession: APIWorkoutSession?

    private func adopt(_ session: APIWorkoutSession) {
        rawSession = session
        activeSessionID = session.id
        focusedExerciseIndex = min(focusedExerciseIndex, max(session.workoutExercises.count - 1, 0))
        active = mapActive(session)
    }

    private func refreshActive() async {
        guard let client, let id = activeSessionID else { return }
        if let session: APIWorkoutSession = try? await client.request(.get, "/workout-sessions/\(id)") {
            adopt(session)
        }
    }

    private func clearActive() {
        rawSession = nil
        activeSessionID = nil
        active = nil
        focusedExerciseIndex = 0
    }

    private func refreshPosition() async {
        // Reload programs so the rotation pointer (current slot) reflects the
        // finish/skip advance the next time the spine/Today renders.
        await programsStore?.load()
    }

    private func focusedRawExercise(in session: APIWorkoutSession) -> APIWorkoutExercise? {
        let sorted = session.workoutExercises.sorted { $0.position < $1.position }
        guard !sorted.isEmpty else { return nil }
        return sorted[min(focusedExerciseIndex, sorted.count - 1)]
    }

    // MARK: - Exercise library

    private func loadExerciseLibraryIfNeeded() async {
        guard let client, !exerciseLibraryLoaded else { return }
        var cursor: String?
        var names: [String: String] = [:]
        for _ in 0..<8 {
            let path = "/exercises?limit=200" + (cursor.map { "&cursor=\($0)" } ?? "")
            guard let page: APIExerciseList = try? await client.request(.get, path) else { break }
            for ex in page.items { names[ex.id] = ex.name }
            cursor = page.nextCursor
            if cursor == nil { break }
        }
        if !names.isEmpty {
            exerciseNames = names
            exerciseLibraryLoaded = true
        }
    }

    private func name(for exerciseID: String) -> String {
        exerciseNames[exerciseID] ?? "Exercise"
    }

    // MARK: - Mapping (API → view models)

    private static func mapHistoryRow(_ s: APIWorkoutSessionListItem) -> MockData.Session {
        MockData.Session(
            date: shortDate(s.startedAt),
            day: s.name ?? "Workout",
            duration: durationLabel(start: s.startedAt, end: s.endedAt),
            sets: 0,
            volume: "—",
            prs: 0
        )
    }

    /// The screen's active-session view model, derived from the live session.
    func mapActive(_ session: APIWorkoutSession) -> ActiveView {
        let exercises = session.workoutExercises.sorted { $0.position < $1.position }
        let focused = min(focusedExerciseIndex, max(exercises.count - 1, 0))

        let rail = exercises.enumerated().map { idx, wex -> RailItem in
            let nm = name(for: wex.exerciseId)
            let done = wex.sets.filter { $0.setType != "warmup" }.count
            return RailItem(
                exerciseID: wex.id,
                name: nm,
                shortName: Self.shortLabel(nm),
                doneSets: done,
                totalSets: max(wex.sets.count, done),
                active: idx == focused
            )
        }

        let activeWex = exercises.isEmpty ? nil : exercises[focused]
        let setRows: [LiveSet] = (activeWex?.sets ?? [])
            .sorted { $0.setIndex < $1.setIndex }
            .enumerated()
            .map { i, s in
                LiveSet(
                    setID: s.id,
                    index: i + 1,
                    weight: s.weightKg.map(Self.trimDecimal) ?? "",
                    reps: s.reps.map(String.init) ?? "",
                    rpe: s.rpe.map(Self.trimDecimal) ?? "",
                    isPR: s.isPr
                )
            }

        let totalSets = exercises.reduce(0) { $0 + $1.sets.count }
        let doneSets = exercises.reduce(0) { $0 + $1.sets.filter { $0.setType != "warmup" }.count }

        return ActiveView(
            kicker: session.name ?? "Workout",
            position: exercises.isEmpty ? "No exercises yet" : "Exercise \(focused + 1) of \(exercises.count)",
            setsComplete: "\(doneSets) of \(totalSets) sets logged",
            rail: rail,
            activeExerciseName: activeWex.map { name(for: $0.exerciseId) } ?? "—",
            activeExerciseID: activeWex?.id,
            sets: setRows
        )
    }

    // MARK: - View models

    /// The active-session view model the screen reads (live counterpart to
    /// `MockData.ActiveSession`).
    struct ActiveView {
        var kicker: String
        var position: String
        var setsComplete: String
        var rail: [RailItem]
        var activeExerciseName: String
        var activeExerciseID: String?
        var sets: [LiveSet]
    }

    struct RailItem: Identifiable {
        var exerciseID: String
        var name: String
        var shortName: String
        var doneSets: Int
        var totalSets: Int
        var active: Bool
        var id: String { exerciseID }
    }

    struct LiveSet: Identifiable {
        var setID: String
        var index: Int
        var weight: String
        var reps: String
        var rpe: String
        var isPR: Bool
        var id: String { setID }
    }

    // MARK: - Formatting helpers

    private static func decimalString(_ v: Double) -> String {
        v == v.rounded() ? String(Int(v)) : String(format: "%.2f", v)
    }

    private static func trimDecimal(_ s: String) -> String {
        guard let d = Double(s) else { return s }
        return d == d.rounded() ? String(Int(d)) : String(d)
    }

    private static func shortLabel(_ name: String) -> String {
        let words = name.split(separator: " ")
        return words.prefix(2).joined(separator: " ")
    }

    private static func clock(_ seconds: Int) -> String {
        String(format: "%d:%02d", seconds / 60, seconds % 60)
    }

    private static let isoParser: ISO8601DateFormatter = {
        let f = ISO8601DateFormatter()
        f.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        return f
    }()
    private static let isoParserNoFraction = ISO8601DateFormatter()

    private static func parse(_ iso: String?) -> Date? {
        guard let iso else { return nil }
        return isoParser.date(from: iso) ?? isoParserNoFraction.date(from: iso)
    }

    private static func shortDate(_ iso: String) -> String {
        guard let date = parse(iso) else { return "—" }
        let f = DateFormatter()
        f.dateFormat = "EEE d"
        return f.string(from: date)
    }

    private static func durationLabel(start: String, end: String?) -> String {
        guard let s = parse(start), let e = end.flatMap(parse) else { return "—" }
        let mins = Int(e.timeIntervalSince(s) / 60)
        return clock(max(mins, 0))
    }

    private static func previewActive() -> ActiveView {
        ActiveView(
            kicker: "Push A · Week 4",
            position: "Exercise 1 of 5",
            setsComplete: "2 of 4 sets logged",
            rail: [
                RailItem(exerciseID: "1", name: "Bench Press", shortName: "Bench Press", doneSets: 2, totalSets: 4, active: true),
                RailItem(exerciseID: "2", name: "Overhead Press", shortName: "Overhead Press", doneSets: 0, totalSets: 4, active: false),
            ],
            activeExerciseName: "Barbell Bench Press",
            activeExerciseID: "1",
            sets: [
                LiveSet(setID: "a", index: 1, weight: "92.5", reps: "8", rpe: "7.5", isPR: false),
                LiveSet(setID: "b", index: 2, weight: "92.5", reps: "8", rpe: "8", isPR: false),
            ]
        )
    }

    private static func message(for error: Error) -> String {
        guard let api = error as? APIError else { return "Something went wrong." }
        switch api {
        case .network: return "Couldn’t reach the server. Check your connection."
        case .decoding: return "We couldn’t read the response from the server."
        case .unauthorized: return "Your session expired. Pull to retry."
        case let .server(status, _, message): return message ?? "Server error (\(status))."
        case .invalidURL: return "Something went wrong."
        }
    }
}
