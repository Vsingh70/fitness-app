//
//  InsightsStore.swift
//  GymApp
//
//  Live, API-backed store for the Insights surface. Mirrors the shipped web
//  `/analytics` (Insights) page:
//   - Stat grid: current-week working sets + tonnage + active-insight count +
//     ISO week (`GET /v1/analytics/volume/current-week`).
//   - Volume-by-muscle heat: current-week per-muscle working sets vs a
//     client-side set-target table (the API summary doesn't ship a target yet).
//   - Tonnage trend: total working tonnage per ISO week over ~8 weeks
//     (`GET /v1/analytics/volume?from=&to=`), summed across muscles.
//   - Weekly insight cards: active analytics insights (`GET /v1/insights`),
//     each with a deep link to the relevant exercise / program.
//
//  Design notes (mirrors ProgramsStore / HealthStore):
//   - Injected with an `APIClient` + `AuthService`. When nil (SwiftUI previews)
//     the store stays offline and seeds from `MockData` so canvases render.
//   - All derived view values are mapped here off the raw wire shapes so the
//     view stays declarative and reuses the existing `MockData` view structs.
//   - Never crashes on a network/decode error: failures land in `loadState`.
//

import SwiftUI

@MainActor
@Observable
final class InsightsStore {

    enum LoadState: Equatable {
        case idle
        case loading
        case loaded
        case failed(String)
    }

    // MARK: View-facing state (mapped into the existing view structs)

    /// Stat grid tiles (Sets/wk, Tonnage/wk, Active insights, Training week).
    private(set) var stats: [MockData.WeekStat] = MockData.insightStats
    /// Per-muscle working sets this week vs target, in display order.
    private(set) var muscleVolumes: [MockData.MuscleVolume] = MockData.muscleVolumes
    /// Total working tonnage per ISO week over the trend window.
    private(set) var tonnageTrend: [MockData.TonnagePoint] = MockData.tonnageTrend
    /// Active insight cards, with their deep links.
    private(set) var cards: [InsightCardVM] = InsightsStore.previewCards

    private(set) var loadState: LoadState = .idle

    /// Headline tonnage value + delta for the trend card (computed off the trend).
    private(set) var weeklyTonnage: Double = 23_180
    private(set) var tonnageDeltaText: String? = "↑ 6% vs prior 4 weeks"

    // MARK: Dependencies

    private let client: APIClient?
    private let auth: AuthService?

    /// Trend window: the last 8 ISO weeks (mirrors web `TREND_WEEKS`).
    private static let trendWeeks = 8

    // MARK: Init

    /// Live init — used by the app shell.
    init(client: APIClient, auth: AuthService) {
        self.client = client
        self.auth = auth
    }

    /// Offline init — used by SwiftUI previews. Keeps the seeded `MockData`.
    init(preview: Bool) {
        self.client = nil
        self.auth = nil
        self.loadState = .loaded
    }

    var hasResolved: Bool {
        switch loadState {
        case .loaded, .failed: return true
        case .idle, .loading: return false
        }
    }

    // MARK: - Load

    /// Fetch current-week volume, the 8-week tonnage trend, and active insights,
    /// then map into the view structs. No-op offline (previews keep the seed).
    func load() async {
        guard let client else { return }
        await auth?.ensureSignedIn()
        loadState = .loading
        do {
            let week: APICurrentWeekVolume = try await client.request(
                .get, "/analytics/volume/current-week"
            )
            let volume: APIVolumeResponse = try await client.request(
                .get, volumePath(weeks: Self.trendWeeks)
            )
            // Insights are non-fatal: a failure shouldn't blank the whole page.
            let insightList: APIInsightList? = try? await client.request(.get, "/insights?limit=50")
            let activeCount = insightList?.items.count ?? cards.count

            muscleVolumes = Self.mapMuscleVolumes(week)
            tonnageTrend = Self.mapTonnageTrend(volume)
            (weeklyTonnage, tonnageDeltaText) = Self.tonnageHeadline(tonnageTrend)
            stats = Self.mapStats(week, activeInsights: activeCount)
            if let insightList { cards = insightList.items.map(InsightCardVM.init) }

            loadState = .loaded
        } catch {
            loadState = .failed(Self.message(for: error))
        }
    }

    // MARK: - Mapping (API → view structs)

    /// Stat grid: Sets/wk, Tonnage/wk, Active insights, Training week. Matches the
    /// four web `StatTile`s. Deltas aren't shipped by the API yet, so we render
    /// the figures without a delta line (the tile renders cleanly without one).
    private static func mapStats(_ w: APICurrentWeekVolume, activeInsights: Int) -> [MockData.WeekStat] {
        [
            .init(label: "Sets / wk", value: figure(w.totalWorkingSetsValue), delta: .neutral("This week")),
            .init(label: "Tonnage / wk", value: compactKg(w.totalTonnageKgValue), unit: "kg", delta: .neutral("This week")),
            .init(label: "Active insights", value: "\(activeInsights)", delta: .neutral(activeInsights == 1 ? "card" : "cards")),
            .init(label: "Training week", value: "\(w.isoWeek)", delta: .neutral("ISO \(w.isoYear)")),
        ]
    }

    /// Map current-week per-muscle working sets into the heat grid's display
    /// order, filling missing muscles with 0. Targets come from the client-side
    /// table (the API summary doesn't ship a per-muscle target yet — mirrors the
    /// web `SET_TARGETS`).
    private static func mapMuscleVolumes(_ w: APICurrentWeekVolume) -> [MockData.MuscleVolume] {
        var byMuscle: [String: Int] = [:]
        for p in w.perMuscle {
            byMuscle[p.muscle] = Int(p.workingSetsValue.rounded())
        }
        return muscleOrder.map { slug in
            MockData.MuscleVolume(
                name: slug.replacingOccurrences(of: "_", with: " "),
                sets: byMuscle[slug] ?? 0,
                target: setTargets[slug] ?? 8
            )
        }
    }

    /// Sum tonnage across all muscle series, bucketed by ISO year+week, ordered
    /// oldest→newest. Mirrors the web `tonnageByWeek`.
    private static func mapTonnageTrend(_ v: APIVolumeResponse) -> [MockData.TonnagePoint] {
        struct Bucket { var order: Int; var tonnage: Double; var week: Int }
        var buckets: [String: Bucket] = [:]
        for series in v.items {
            for p in series.points {
                let key = "\(p.isoYear)-\(String(format: "%02d", p.isoWeek))"
                let order = p.isoYear * 100 + p.isoWeek
                if buckets[key] != nil {
                    buckets[key]!.tonnage += p.tonnageKgValue
                } else {
                    buckets[key] = Bucket(order: order, tonnage: p.tonnageKgValue, week: p.isoWeek)
                }
            }
        }
        return buckets.values
            .sorted { $0.order < $1.order }
            .map { MockData.TonnagePoint(week: $0.week, kg: $0.tonnage.rounded()) }
    }

    /// Headline figure (latest week) + a delta vs the prior 4 weeks' mean.
    private static func tonnageHeadline(_ trend: [MockData.TonnagePoint]) -> (Double, String?) {
        guard let latest = trend.last else { return (0, nil) }
        let prior = trend.dropLast().suffix(4)
        guard !prior.isEmpty else { return (latest.kg, nil) }
        let priorMean = prior.map(\.kg).reduce(0, +) / Double(prior.count)
        guard priorMean > 0 else { return (latest.kg, nil) }
        let pct = (latest.kg - priorMean) / priorMean * 100
        let rounded = Int(pct.rounded())
        if rounded == 0 { return (latest.kg, "≈ flat vs prior 4 weeks") }
        let arrow = rounded > 0 ? "↑" : "↓"
        return (latest.kg, "\(arrow) \(abs(rounded))% vs prior 4 weeks")
    }

    // MARK: - Paths

    private func volumePath(weeks: Int) -> String {
        let cal = Calendar(identifier: .gregorian)
        let to = Date()
        let from = cal.date(byAdding: .day, value: -weeks * 7, to: to) ?? to
        let fmt = DateFormatter()
        fmt.locale = Locale(identifier: "en_US_POSIX")
        fmt.timeZone = TimeZone(identifier: "UTC")
        fmt.dateFormat = "yyyy-MM-dd"
        return "/analytics/volume?from=\(fmt.string(from: from))&to=\(fmt.string(from: to))"
    }

    // MARK: - Formatting helpers

    private static func figure(_ n: Double) -> String {
        let v = Int(n.rounded())
        return v.formatted(.number.grouping(.automatic))
    }

    /// `23180` → `"23,180"`; only compacts to `"k"` at very large magnitudes so
    /// the figure tile keeps the editorial big-number feel.
    private static func compactKg(_ n: Double) -> String {
        let v = n.rounded()
        if v >= 100_000 { return "\(String(format: "%.0f", v / 1000))k" }
        return Int(v).formatted(.number.grouping(.automatic))
    }

    private static func message(for error: any Error) -> String {
        if let api = error as? APIError {
            switch api {
            case .server(_, _, let msg?): return msg
            case .unauthorized: return "Your session expired. Pull to retry."
            default: return "Couldn’t reach the server."
            }
        }
        return "Something went wrong."
    }

    // MARK: - Muscle order + targets (mirrors web muscle-heatmap.tsx)

    /// Display order for the 19 muscles, grouped head-to-toe like the web grid.
    static let muscleOrder: [String] = [
        "chest", "front_delts", "side_delts", "rear_delts", "traps", "rhomboids",
        "lats", "lower_back", "biceps", "triceps", "forearms", "abs", "obliques",
        "glutes", "quads", "hamstrings", "adductors", "abductors", "calves",
    ]

    /// Per-muscle weekly working-set targets (the web `SET_TARGETS` stand-in).
    static let setTargets: [String: Int] = [
        "chest": 12, "front_delts": 8, "side_delts": 9, "rear_delts": 9,
        "traps": 8, "rhomboids": 9, "lats": 12, "lower_back": 8, "biceps": 10,
        "triceps": 10, "forearms": 6, "abs": 8, "obliques": 6, "glutes": 10,
        "quads": 12, "hamstrings": 10, "adductors": 6, "abductors": 6, "calves": 9,
    ]

    // MARK: - Preview seed

    static let previewCards: [InsightCardVM] = [
        InsightCardVM(APIInsight(
            id: "p1", kind: "pr_streak", severity: "info",
            title: "Three PRs this week",
            body: "Bench, OHP, Bulgarian split squat all moved up.", rationale: nil
        )),
        InsightCardVM(APIInsight(
            id: "p2", kind: "stagnation", severity: "action",
            title: "Pull-ups have stalled",
            body: "Three sessions flat. Try a deload or rest-pause.", rationale: nil,
            payload: APIInsightPayload(exerciseId: "00000000-0000-0000-0000-000000000001")
        )),
        InsightCardVM(APIInsight(
            id: "p3", kind: "weak_muscle", severity: "warn",
            title: "Rear delts look underdeveloped",
            body: "Below the typical band for your bodyweight.", rationale: nil
        )),
    ]
}

// MARK: - Insight card view model

/// A presentable insight card with its severity tone, kind label, and deep-link
/// target. Built from an `APIInsight` (mirrors the web `InsightCard`).
struct InsightCardVM: Identifiable, Equatable {

    /// Where a card's CTA navigates. Mirrors the web precedence: a concrete
    /// exercise UUID → the exercise analytics; a program-shaped kind → the
    /// program spine; otherwise no deep link.
    enum Destination: Equatable {
        case exercise(id: String)
        case programs
        case none
    }

    let id: String
    let kindLabel: String
    let title: String
    let body: String?
    let severity: String
    let destination: Destination

    /// CTA label, matching the web ("View exercise" / "Adjust program").
    var ctaLabel: String? {
        switch destination {
        case .exercise: return "View exercise"
        case .programs: return "Adjust program"
        case .none: return nil
        }
    }

    /// Left-rail / kicker tone keyed off severity (info→success, warn→warning,
    /// action→accent — same mapping as the web `SEVERITY_BORDER`).
    var tone: Color {
        switch severity {
        case "info": return .success
        case "warn": return .warning
        case "action": return .accent
        default: return .accent
        }
    }

    init(_ insight: APIInsight) {
        self.id = insight.id
        self.kindLabel = Self.kindLabel(insight.kind)
        self.title = insight.title
        self.body = insight.displayBody
        self.severity = insight.severity
        self.destination = Self.destination(for: insight)
    }

    private static let uuidRE = try! NSRegularExpression(
        pattern: "^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
        options: [.caseInsensitive]
    )

    /// Program-shaped kinds deep-link to the program spine (mirrors web
    /// `PROGRAM_KINDS`).
    private static let programKinds: Set<String> = [
        "weak_muscle", "strong_muscle", "imbalance", "undertrained",
        "volume_drop", "frequency_drop",
    ]

    private static func destination(for insight: APIInsight) -> Destination {
        if let raw = insight.payload?.exerciseId, isUUID(raw) {
            return .exercise(id: raw)
        }
        if programKinds.contains(insight.kind) {
            return .programs
        }
        return .none
    }

    private static func isUUID(_ s: String) -> Bool {
        let range = NSRange(s.startIndex..<s.endIndex, in: s)
        return uuidRE.firstMatch(in: s, options: [], range: range) != nil
    }

    /// Kind → display label (mirrors web `KIND_LABEL`).
    private static func kindLabel(_ kind: String) -> String {
        switch kind {
        case "stagnation": return "Plateau"
        case "volume_drop": return "Volume drop"
        case "frequency_drop": return "Frequency drop"
        case "pr_streak": return "PR streak"
        case "weak_muscle": return "Weak point"
        case "strong_muscle": return "Strong point"
        case "imbalance": return "Imbalance"
        case "undertrained": return "Undertrained"
        default: return kind.replacingOccurrences(of: "_", with: " ").capitalized
        }
    }
}
