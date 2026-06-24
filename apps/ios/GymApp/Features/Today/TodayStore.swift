//
//  TodayStore.swift
//  GymApp
//
//  Live, API-backed store for the Today command center — the daily landing
//  surface that answers "what do I do now". Mirrors the shipped web `/` page:
//   - Today's session: the active program's current rotation slot, resolved via
//     `ProgramsStore` (its `active` program + `position(for:)`), with a live
//     start-session action that mirrors the web "Start →".
//   - Readiness: `GET /v1/readiness/today` (score + band, or a "Connect" state
//     when the wearable has no data).
//   - Nutrition: `GET /v1/nutrition/day?date=` + `GET /v1/nutrition/targets`
//     for the quick meal-log masthead.
//   - Insights: `GET /v1/insights` — the top 1–3 active cards.
//
//  Design notes (mirrors ProgramsStore / HealthStore):
//   - Injected with an `APIClient` + `AuthService` + the shared `ProgramsStore`.
//     When those are nil (SwiftUI previews) the store stays offline and seeds
//     sample data so canvases render without a network.
//   - Never crashes on a network/decode error: each surface degrades
//     independently (a failed nutrition fetch doesn't blank readiness, etc.).
//   - All derived view values are computed here off the raw wire shapes so the
//     view stays declarative.
//

import SwiftUI

@MainActor
@Observable
final class TodayStore {

    enum LoadState: Equatable {
        case idle
        case loading
        case loaded
        case failed(String)
    }

    // MARK: View-facing state

    /// The active program (mirrors `ProgramsStore.active`), nil when none.
    private(set) var activeProgram: MockData.Program?
    /// The live rotation position for the active program (today's slot / next).
    private(set) var position: APIPosition?

    /// Today's readiness (score/band), nil until resolved or when no wearable data.
    private(set) var readiness: APIReadinessToday?

    /// Today's nutrition totals + targets for the quick-log masthead.
    private(set) var nutrition: APIDaySummary?
    private(set) var nutritionTargets: APIMealPlanTargets?

    /// The top 1–3 active insight cards.
    private(set) var insights: [APIInsight] = []

    private(set) var loadState: LoadState = .idle
    /// True while a start-session POST is in flight (drives the Start button).
    private(set) var isStartingSession = false

    // MARK: Dependencies

    private let client: APIClient?
    private let auth: AuthService?
    private let programsStore: ProgramsStore?

    // MARK: Init

    /// Live init — used by the app shell. Reuses the shared `ProgramsStore` for
    /// the program rotation rather than re-fetching the program list.
    init(client: APIClient, auth: AuthService, programsStore: ProgramsStore) {
        self.client = client
        self.auth = auth
        self.programsStore = programsStore
    }

    /// Offline init — used by SwiftUI previews. Seeds sample data so the canvas
    /// renders without a network.
    init(preview: Bool) {
        let previewPrograms = ProgramsStore()
        self.client = nil
        self.auth = nil
        self.programsStore = previewPrograms
        self.activeProgram = previewPrograms.active
        self.readiness = APIReadinessToday(date: "2026-06-23", score: 78, band: "high", hasData: true)
        self.nutrition = APIDaySummary(
            date: "2026-06-23",
            totals: APIDayMacros(kcal: "1620.00", proteinG: "134.00", carbsG: "168.00", fatG: "51.00", fiberG: "24.00")
        )
        self.nutritionTargets = APIMealPlanTargets(
            targetKcal: "2680", targetProteinG: "180", targetCarbsG: "300", targetFatG: "80"
        )
        self.insights = TodayStore.previewInsights
        self.loadState = .loaded
    }

    var hasResolved: Bool {
        switch loadState {
        case .loaded, .failed: return true
        case .idle, .loading: return false
        }
    }

    // MARK: - Load

    /// Fetch every Today surface. The program rotation comes from the shared
    /// `ProgramsStore` (ensuring it's loaded first); readiness / nutrition /
    /// insights are fetched here. Each surface degrades independently.
    func load() async {
        guard let client else { return }
        await auth?.ensureSignedIn()
        loadState = .loading

        // Program rotation — reuse the shared store; load it if it hasn't yet.
        if let programsStore {
            if !programsStore.hasResolved { await programsStore.load() }
            activeProgram = programsStore.active
            if let active = activeProgram {
                position = await programsStore.position(for: active)
            } else {
                position = nil
            }
        }

        // Readiness — non-fatal; the tile shows a "Connect" state when absent.
        readiness = try? await client.request(.get, "/readiness/today")

        // Nutrition — totals always present; targets 409 when the profile is
        // incomplete, so treat a missing targets as "set up your plan".
        nutrition = try? await client.request(.get, "/nutrition/day?date=\(Self.isoToday())")
        nutritionTargets = try? await client.request(.get, "/nutrition/targets")

        // Insights — top 1–3.
        if let list: APIInsightList = try? await client.request(.get, "/insights?limit=3") {
            insights = Array(list.items.prefix(3))
        }

        loadState = .loaded
    }

    // MARK: - Start session

    /// Start a workout from the active program's current rotation slot
    /// (`POST /v1/programs/{id}/start-session`). Mirrors the web "Start →".
    /// Returns the new session id on success, nil on failure / offline.
    @discardableResult
    func startSession() async -> String? {
        guard let client, let programsStore, let active = activeProgram,
              let serverID = programsStore.serverID(for: active) else { return nil }
        isStartingSession = true
        defer { isStartingSession = false }
        do {
            let session: APIWorkoutSession = try await client.request(
                .post, "/programs/\(serverID)/start-session"
            )
            return session.id
        } catch {
            return nil
        }
    }

    // MARK: - Derived: Session card

    /// The slot to show on the card: prefer the server-resolved `today_slot`,
    /// else the active program's day matching `current_slot_index`, else first.
    var todaySlot: MockData.ProgramDay? {
        guard let active = activeProgram else { return nil }
        if let serverSlot = position?.todaySlot {
            // Match the mapped view-day by slot index (the view structs don't
            // carry server ids, but slot_index is stable within a microcycle).
            if let day = active.days.first(where: { $0.slotIndex == serverSlot.slotIndex }) {
                return day
            }
        }
        if let idx = position?.currentSlotIndex,
           let day = active.days.first(where: { $0.slotIndex == idx }) {
            return day
        }
        return active.days.first
    }

    /// The next training slot's display name (rest-state copy).
    var nextTrainingName: String? {
        if let server = position?.nextTrainingSlot { return server.name }
        guard let active = activeProgram, let today = todaySlot else { return nil }
        let count = active.days.count
        guard count > 0 else { return nil }
        for offset in 1...count {
            let idx = (today.slotIndex + offset) % count
            if let day = active.days.first(where: { $0.slotIndex == idx }), !day.isRestDay {
                return day.name
            }
        }
        return nil
    }

    /// Total programmed sets across the today slot (drives the ~min estimate).
    var todaySetCount: Int {
        todaySlot?.exercises.reduce(0) { $0 + $1.sets } ?? 0
    }

    /// Estimated minutes for the today slot (web heuristic: 2.5 min / set).
    var todayEstimatedMinutes: Int {
        Int((Double(todaySetCount) * 2.5).rounded())
    }

    var inDeload: Bool { position?.inDeload ?? false }

    /// "Microcycle N" badge, nil when unavailable.
    var microcycleLabel: String? {
        position.map { "Microcycle \($0.currentMicrocycleNumber)" }
    }

    // MARK: - Derived: Readiness

    var readinessScore: Int? { readiness?.score }
    var hasReadiness: Bool { readiness?.score != nil }

    /// Band copy + tone, mirroring the web `ReadinessCard`.
    var readinessBand: (copy: String, color: Color)? {
        switch readiness?.band {
        case "high": return ("Push it", .success)
        case "moderate": return ("Workable", .warning)
        case "low": return ("Take it easy", .destructive)
        default: return nil
        }
    }

    /// 0...1 ring fraction for the readiness score.
    var readinessFraction: Double {
        guard let s = readiness?.score else { return 0 }
        return min(max(Double(s) / 100, 0), 1)
    }

    // MARK: - Derived: Nutrition

    var nutritionKcal: Int { Int(Double(nutrition?.totals.kcal ?? "0") ?? 0) }
    var nutritionTargetKcal: Int? { nutritionTargets.flatMap { Int(Double($0.targetKcal) ?? 0) } }
    var nutritionProtein: Int { Int(Double(nutrition?.totals.proteinG ?? "0") ?? 0) }
    var nutritionCarbs: Int { Int(Double(nutrition?.totals.carbsG ?? "0") ?? 0) }
    var nutritionFat: Int { Int(Double(nutrition?.totals.fatG ?? "0") ?? 0) }

    /// kcal remaining vs. target (nil when no target derived).
    var nutritionRemaining: Int? {
        nutritionTargetKcal.map { max($0 - nutritionKcal, 0) }
    }

    /// 0...1 progress toward the calorie target.
    var nutritionFraction: Double {
        guard let target = nutritionTargetKcal, target > 0 else { return 0 }
        return min(max(Double(nutritionKcal) / Double(target), 0), 1)
    }

    // MARK: - Helpers

    private static func isoToday() -> String {
        let fmt = DateFormatter()
        fmt.locale = Locale(identifier: "en_US_POSIX")
        fmt.dateFormat = "yyyy-MM-dd"
        return fmt.string(from: Date())
    }

    /// "Monday" kicker + "Monday, June 23" long date for the header.
    static func headerKicker(_ date: Date = Date()) -> String {
        let fmt = DateFormatter()
        fmt.dateFormat = "EEEE"
        return fmt.string(from: date)
    }

    static func headerLong(_ date: Date = Date()) -> String {
        let fmt = DateFormatter()
        fmt.dateFormat = "EEEE, MMMM d"
        return fmt.string(from: date)
    }

    // MARK: - Preview seed

    static let previewInsights: [APIInsight] = [
        APIInsight(
            id: "1", kind: "increase_weight", severity: "action",
            title: "Bench press is ready to progress",
            body: "8/8/7 reps @ RPE 7.5–9 last session — top of range.",
            rationale: "Add 2.5 kg next session.",
            subject: "Bench press", surfacedAt: nil, dismissedAt: nil
        ),
        APIInsight(
            id: "2", kind: "weak_muscle", severity: "warn",
            title: "Rear delts are undertrained",
            body: "Below your weekly volume target for two weeks.",
            rationale: "Add a face-pull set.",
            subject: "Rear delts", surfacedAt: nil, dismissedAt: nil
        )
    ]
}
