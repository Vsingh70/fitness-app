//
//  HealthStore.swift
//  GymApp
//
//  Live, API-backed store for the Health surface — the merged Body + Wearable
//  view that mirrors the shipped web `/health` page. Loads:
//   - Metrics: `GET /v1/body-metrics` (logged weight history) and supports
//     logging a new weight via `POST /v1/body-metrics`.
//   - Wearable: `GET /v1/readiness/history?from=&to=` (synced steps / sleep /
//     resting HR / HRV) and `GET /v1/integrations/health/status` (the one
//     wearable connection: Fitbit via Google Health).
//
//  Design notes (mirrors ProgramsStore):
//   - Injected with an `APIClient` + `AuthService`. When nil (SwiftUI previews)
//     the store stays offline and seeds sample data so canvases render.
//   - Never crashes on a network/decode error: failures land in `loadState`
//     and surface as an inline retry in the view.
//   - All derived view values (current weight, weekly delta, latest tiles) are
//     computed here off the raw wire shapes so the views stay declarative.
//

import SwiftUI

@MainActor
@Observable
final class HealthStore {

    enum LoadState: Equatable {
        case idle
        case loading
        case loaded
        case failed(String)
    }

    // MARK: View-facing state

    /// Body-metric readings, newest-first (as the API returns them).
    private(set) var metrics: [APIBodyMetric] = []
    /// Readiness/wearable days, newest-first (sorted on load).
    private(set) var readiness: [APIReadinessDay] = []
    /// The wearable connection status, nil until the first load resolves.
    private(set) var wearable: APIHealthStatus?

    private(set) var loadState: LoadState = .idle
    /// True while a weight POST is in flight (drives the sheet's Save button).
    private(set) var isLoggingWeight = false

    // MARK: Dependencies

    private let client: APIClient?
    private let auth: AuthService?

    // MARK: Init

    /// Live init — used by the app shell.
    init(client: APIClient, auth: AuthService) {
        self.client = client
        self.auth = auth
    }

    /// Offline init — used by SwiftUI previews. Seeds sample data so the
    /// canvases render without a network.
    init(preview: Bool) {
        self.client = nil
        self.auth = nil
        self.metrics = HealthStore.previewMetrics
        self.readiness = HealthStore.previewReadiness
        self.wearable = APIHealthStatus(
            connected: true, needsReauth: false,
            lastSyncedAt: "2026-06-23T20:00:00Z",
            lastSyncedActivityAt: nil, scopes: []
        )
        self.loadState = .loaded
    }

    var hasResolved: Bool {
        switch loadState {
        case .loaded, .failed: return true
        case .idle, .loading: return false
        }
    }

    // MARK: - Load

    /// Fetch body metrics, readiness history (last 30 days), and wearable status.
    func load() async {
        guard let client else { return }
        await auth?.ensureSignedIn()
        loadState = .loading
        do {
            let metricsList: APIBodyMetricList = try await client.request(.get, "/body-metrics?limit=60")
            let history: APIReadinessHistory = try await client.request(.get, readinessHistoryPath(days: 30))
            // Wearable status is non-fatal: a failure here shouldn't blank the page.
            let status: APIHealthStatus? = try? await client.request(.get, "/integrations/health/status")

            metrics = metricsList.items
            readiness = history.items.sorted { $0.date > $1.date }
            wearable = status
            loadState = .loaded
        } catch {
            loadState = .failed(Self.message(for: error))
        }
    }

    /// Log a new body weight (stored in kg on the backend). `displayValue` is in
    /// the user's chosen unit; we convert to kg for the wire. Reloads on success.
    func logWeight(displayValue: Double, unit: WeightUnit) async {
        guard let client else { return }
        isLoggingWeight = true
        defer { isLoggingWeight = false }
        let kg = unit == .lb ? displayValue / Self.kgPerLb : displayValue
        let body = APIBodyMetricCreate(
            weightKg: String(format: "%.2f", kg),
            recordedAt: Self.iso8601Now()
        )
        do {
            try await client.requestVoid(.post, "/body-metrics", body: body)
            await load()
        } catch {
            // Keep prior state; surface failure on the next load if it persists.
            loadState = .failed(Self.message(for: error))
        }
    }

    // MARK: - Derived: Metrics

    /// Newest reading that actually carries a weight.
    var latestWeighted: APIBodyMetric? {
        metrics.first { $0.weightKgValue != nil }
    }

    /// Current weight in display units, rounded to 1dp. nil when none logged.
    func currentWeight(unit: WeightUnit) -> Double? {
        guard let kg = latestWeighted?.weightKgValue else { return nil }
        return Self.round1(unit == .lb ? kg * Self.kgPerLb : kg)
    }

    /// Weekly change in display units + the raw-kg sign for arrow direction.
    /// latest = newest weighted row; prior = first subsequent weighted row >= 7
    /// days older (fallback: oldest weighted row). nil with < 2 weighted rows.
    func weeklyDelta(unit: WeightUnit) -> (display: Double, kgSign: Double)? {
        let weighted = metrics.filter { $0.weightKgValue != nil } // newest-first
        guard weighted.count >= 2,
              let latest = weighted.first,
              let latestKg = latest.weightKgValue,
              let latestTime = Self.instant(latest.recordedAt) else { return nil }
        let sevenDays: TimeInterval = 7 * 24 * 60 * 60
        let prior = weighted.dropFirst().first { row in
            guard let t = Self.instant(row.recordedAt) else { return false }
            return latestTime - t >= sevenDays
        } ?? weighted.last
        guard let priorKg = prior?.weightKgValue else { return nil }
        let kgDelta = latestKg - priorKg
        let display = Self.round1(
            (unit == .lb ? latestKg * Self.kgPerLb : latestKg)
                - (unit == .lb ? priorKg * Self.kgPerLb : priorKg)
        )
        return (display, kgDelta)
    }

    /// "Today" / "Yesterday" / "3d ago" / "Jun 6" for the latest reading.
    var lastLoggedRelative: String? {
        latestWeighted.map { Self.relativeDate($0.recordedAt) }
    }

    // MARK: - Derived: Wearable tiles (latest non-null per metric)

    var latestSteps: Int? { readiness.compactMap { $0.steps }.first }
    var latestSleepMinutes: Int? { readiness.compactMap { $0.sleepMinutes }.first }
    var latestRestingHr: Int? { readiness.compactMap { $0.restingHr }.first }
    var latestHrv: Double? { readiness.compactMap { $0.hrvMsValue }.first }

    // MARK: - Paths / helpers

    private func readinessHistoryPath(days: Int) -> String {
        let cal = Calendar(identifier: .gregorian)
        let to = Date()
        let from = cal.date(byAdding: .day, value: -days, to: to) ?? to
        let fmt = DateFormatter()
        fmt.locale = Locale(identifier: "en_US_POSIX")
        fmt.timeZone = TimeZone(identifier: "UTC")
        fmt.dateFormat = "yyyy-MM-dd"
        return "/readiness/history?from=\(fmt.string(from: from))&to=\(fmt.string(from: to))"
    }

    static let kgPerLb = 2.20462

    static func round1(_ n: Double) -> Double {
        let r = (n * 10).rounded() / 10
        return r == 0 ? 0 : r
    }

    private static func iso8601Now() -> String {
        let fmt = ISO8601DateFormatter()
        fmt.formatOptions = [.withInternetDateTime]
        return fmt.string(from: Date())
    }

    /// Parse a date-only (`YYYY-MM-DD`) or full ISO-8601 instant to seconds.
    static func instant(_ iso: String) -> TimeInterval? {
        if iso.count == 10 {
            let fmt = DateFormatter()
            fmt.locale = Locale(identifier: "en_US_POSIX")
            fmt.timeZone = TimeZone(identifier: "UTC")
            fmt.dateFormat = "yyyy-MM-dd"
            return fmt.date(from: iso)?.timeIntervalSince1970
        }
        let fmt = ISO8601DateFormatter()
        fmt.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        if let d = fmt.date(from: iso) { return d.timeIntervalSince1970 }
        fmt.formatOptions = [.withInternetDateTime]
        return fmt.date(from: iso)?.timeIntervalSince1970
    }

    /// "Today" / "Yesterday" / "Nd ago" (<7) else "Jun 6".
    static func relativeDate(_ iso: String) -> String {
        guard let t = instant(iso) else { return iso }
        let date = Date(timeIntervalSince1970: t)
        let cal = Calendar.current
        let days = cal.dateComponents([.day],
            from: cal.startOfDay(for: date),
            to: cal.startOfDay(for: Date())).day ?? 0
        if days <= 0 { return "Today" }
        if days == 1 { return "Yesterday" }
        if days < 7 { return "\(days)d ago" }
        let fmt = DateFormatter()
        fmt.dateFormat = "MMM d"
        return fmt.string(from: date)
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

    // MARK: - Preview seed

    static let previewMetrics: [APIBodyMetric] = [
        APIBodyMetric(id: "1", recordedAt: "2026-06-22T08:00:00Z", weightKg: "81.90",
                      bodyFatPct: nil, neckCm: nil, waistCm: nil, hipCm: nil,
                      createdAt: "2026-06-22T08:00:00Z"),
        APIBodyMetric(id: "2", recordedAt: "2026-06-15T08:00:00Z", weightKg: "82.50",
                      bodyFatPct: nil, neckCm: nil, waistCm: nil, hipCm: nil,
                      createdAt: "2026-06-15T08:00:00Z")
    ]
    static let previewReadiness: [APIReadinessDay] = [
        APIReadinessDay(date: "2026-06-22", score: 82, band: "ready",
                        hrvMs: "48.2", restingHr: 54, sleepMinutes: 444, steps: 12438)
    ]
}
