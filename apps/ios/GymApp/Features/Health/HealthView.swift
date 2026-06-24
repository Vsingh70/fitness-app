//
//  HealthView.swift
//  GymApp
//
//  Health — the merged Body + Wearable surface, mirroring the shipped web
//  `/health` page. Two labeled sections:
//   - Metrics: logged weight (current / weekly change / last logged), a weight
//     history list, and a "Log weight" action.
//   - Wearable: the one wearable connection card plus synced steps / sleep /
//     resting HR / HRV tiles.
//
//  Backed by `HealthStore` (live API). Styled entirely through Core/Design.
//

import SwiftUI

struct HealthView: View {
    @Environment(HealthStore.self) private var store
    @Environment(SettingsStore.self) private var settings
    @State private var showLogWeight = false

    private var unit: WeightUnit { settings.weightUnit }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 28) {
                ScreenHeader(
                    title: "Health",
                    subtitle: "Metrics + wearable"
                )

                switch store.loadState {
                case .loading where store.metrics.isEmpty && store.readiness.isEmpty:
                    HealthLoadingView()
                case .failed(let message) where store.metrics.isEmpty && store.readiness.isEmpty:
                    HealthErrorView(message: message) {
                        Task { await store.load() }
                    }
                    .padding(.horizontal, 20)
                default:
                    metricsSection
                    wearableSection
                }
            }
            .padding(.bottom, 32)
        }
        .background(Color.bg)
        .scrollIndicators(.hidden)
        .refreshable { await store.load() }
        .sheet(isPresented: $showLogWeight) {
            LogWeightSheet(unit: unit) { value in
                await store.logWeight(displayValue: value, unit: unit)
            }
        }
    }

    // MARK: - Metrics (formerly Body)

    private var metricsSection: some View {
        VStack(alignment: .leading, spacing: 16) {
            HStack(alignment: .bottom) {
                VStack(alignment: .leading, spacing: 4) {
                    Text("Metrics").kicker()
                    Text("Body weight and composition over time.")
                        .font(.footnote).foregroundStyle(.ink2)
                }
                Spacer(minLength: 8)
                Button("Log weight") { showLogWeight = true }
                    .buttonStyle(.editorialSmallTonal)
            }

            HStack(spacing: 8) {
                StatTile(
                    label: "Current weight",
                    value: store.currentWeight(unit: unit).map { Self.trim($0) } ?? "—",
                    unit: store.currentWeight(unit: unit) != nil ? unit.title : nil
                )
                StatTile(
                    label: "Weekly change",
                    value: weeklyChangeValue,
                    unit: store.weeklyDelta(unit: unit) != nil ? unit.title : nil,
                    delta: weeklyChangeDelta
                )
                StatTile(
                    label: "Last logged",
                    value: store.lastLoggedRelative ?? "—"
                )
            }

            historyCard
        }
        .padding(.horizontal, 20)
    }

    private var weeklyChangeValue: String {
        guard let d = store.weeklyDelta(unit: unit) else { return "—" }
        let sign = d.display >= 0 ? "+" : "−"
        return "\(sign)\(Self.trim(abs(d.display)))"
    }

    private var weeklyChangeDelta: StatDelta? {
        guard let d = store.weeklyDelta(unit: unit) else { return nil }
        if d.kgSign > 0 { return .up("vs last week") }
        if d.kgSign < 0 { return .down("vs last week") }
        return .neutral("vs last week")
    }

    private var historyCard: some View {
        VStack(alignment: .leading, spacing: 0) {
            SectionHeaderLarge(title: "Weight history")
                .padding(.bottom, 4)
            if store.metrics.isEmpty {
                Text("No weight logged yet.")
                    .font(.system(size: 16, design: .serif))
                    .foregroundStyle(.ink2)
                    .padding(.vertical, 20)
            } else {
                ForEach(Array(store.metrics.prefix(12).enumerated()), id: \.element.id) { index, m in
                    weightRow(m, showsSeparator: index < min(store.metrics.count, 12) - 1)
                }
            }
        }
    }

    private func weightRow(_ m: APIBodyMetric, showsSeparator: Bool) -> some View {
        VStack(spacing: 0) {
            HStack {
                Text(HealthStore.relativeDate(m.recordedAt))
                    .font(.bodyText).foregroundStyle(.ink)
                Spacer()
                if let kg = m.weightKgValue {
                    let display = unit == .lb ? kg * HealthStore.kgPerLb : kg
                    HStack(alignment: .firstTextBaseline, spacing: 3) {
                        Text(Self.trim(HealthStore.round1(display)))
                            .font(.system(size: 15, weight: .semibold))
                            .monospacedDigit().foregroundStyle(.ink)
                        Text(unit.title).font(.caption).foregroundStyle(.ink2)
                    }
                } else {
                    Text("—").foregroundStyle(.ink3)
                }
            }
            .frame(minHeight: 44)
            .padding(.vertical, 4)
            if showsSeparator {
                Rectangle().fill(Color.hairline).frame(height: 1)
            }
        }
    }

    // MARK: - Wearable (formerly Health)

    private var wearableSection: some View {
        VStack(alignment: .leading, spacing: 16) {
            VStack(alignment: .leading, spacing: 4) {
                Text("Wearable").kicker()
                Text("Daily steps, sleep, and recovery synced from your watch.")
                    .font(.footnote).foregroundStyle(.ink2)
            }

            WearableConnectionCard(status: store.wearable, isLoading: store.loadState == .loading)

            HStack(spacing: 8) {
                StatTile(label: "Steps", value: Self.formatSteps(store.latestSteps))
                StatTile(label: "Last sleep", value: Self.formatSleep(store.latestSleepMinutes))
            }
            HStack(spacing: 8) {
                StatTile(label: "Resting HR", value: Self.formatHr(store.latestRestingHr))
                StatTile(label: "HRV", value: Self.formatHrv(store.latestHrv))
            }
        }
        .padding(.horizontal, 20)
    }

    // MARK: - Formatting (mirrors web format-health.ts)

    /// 81.9 → "81.9"; 82.0 → "82". Drops a trailing ".0".
    static func trim(_ n: Double) -> String {
        n == n.rounded() ? String(Int(n.rounded())) : String(format: "%g", n)
    }

    static func formatSteps(_ n: Int?) -> String {
        guard let n else { return "—" }
        let fmt = NumberFormatter()
        fmt.numberStyle = .decimal
        return fmt.string(from: NSNumber(value: n)) ?? "\(n)"
    }

    static func formatSleep(_ minutes: Int?) -> String {
        guard let minutes else { return "—" }
        let total = max(0, minutes)
        return "\(total / 60)h \(total % 60)m"
    }

    static func formatHr(_ n: Int?) -> String { n.map { "\($0) bpm" } ?? "—" }

    static func formatHrv(_ n: Double?) -> String { n.map { "\(Int($0.rounded())) ms" } ?? "—" }
}

// MARK: - Loading / error (editorial)

struct HealthLoadingView: View {
    var body: some View {
        VStack(spacing: 14) {
            ProgressView().controlSize(.large).tint(.ink3)
            Text("Loading health")
                .font(.system(size: 11, weight: .semibold))
                .textCase(.uppercase).tracking(1.2)
                .foregroundStyle(.ink3)
        }
        .frame(maxWidth: .infinity, minHeight: 240)
        .padding(40)
    }
}

struct HealthErrorView: View {
    let message: String
    let retry: () -> Void
    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            Text("Couldn’t load health").kicker()
            Text(message)
                .font(.system(size: 16, design: .serif))
                .foregroundStyle(.ink2)
                .fixedSize(horizontal: false, vertical: true)
            Button(action: retry) {
                Label("Try again", systemImage: "arrow.clockwise")
            }
            .buttonStyle(.editorialSecondary)
            .padding(.top, 4)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(.vertical, 12)
    }
}

#Preview {
    NavigationStack {
        HealthView()
            .environment(HealthStore(preview: true))
            .environment(SettingsStore())
            .environment(\.editorialAccent, AccentChoice.clay.color(for: .light))
    }
}
