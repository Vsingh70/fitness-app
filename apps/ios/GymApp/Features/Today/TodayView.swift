//
//  TodayView.swift
//  GymApp
//
//  Today — the command center. The daily landing surface and the answer to
//  "what do I do now": a readiness tile (from Health/readiness), today's session
//  card (the active program's current rotation slot, with Start), a quick
//  meal-log entry, and a short insights feed (top 1–3). Mirrors the shipped web
//  `/` page. Driven by `TodayStore` (live API) — no MockData reads.
//

import SwiftUI

struct TodayView: View {
    @Environment(\.editorialAccent) private var accent
    @Environment(TodayStore.self) private var store

    /// Set after a successful start-session; presents the in-progress session.
    @State private var startedSessionID: String?
    @State private var showingActiveSession = false

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 0) {
                    header
                    readinessTile
                    sessionCard
                    quickMealLog
                    insightsFeed
                }
                .padding(.bottom, 28)
            }
            .background(Color.bg)
            .scrollIndicators(.hidden)
            .toolbar(.hidden, for: .navigationBar)
            .navigationDestination(isPresented: $showingActiveSession) {
                ActiveSessionView()
            }
        }
    }

    // MARK: Header

    private var header: some View {
        ScreenHeader(title: TodayStore.headerLong(), subtitle: TodayStore.headerKicker()) {
            MonogramBadge(text: MockData.userInitials)
        }
    }

    // MARK: Readiness tile

    @ViewBuilder
    private var readinessTile: some View {
        if store.hasReadiness {
            HairlineCard {
                HStack(spacing: 16) {
                    ZStack {
                        ActivityRing(
                            value: store.readinessFraction, size: 76, lineWidth: 6,
                            color: store.readinessBand?.color
                        )
                        Text("\(store.readinessScore ?? 0)")
                            .font(.figureSmall).monospacedDigit().foregroundStyle(.ink)
                    }
                    VStack(alignment: .leading, spacing: 2) {
                        Text("Readiness").kicker()
                        if let band = store.readinessBand {
                            Text(band.copy).font(.headline).foregroundStyle(band.color)
                        }
                        NavigationLink {
                            HealthView()
                        } label: {
                            Text("From your wearable →")
                                .font(.caption).foregroundStyle(.ink2)
                        }
                        .buttonStyle(.plain)
                        .padding(.top, 2)
                    }
                    Spacer()
                }
            }
            .padding(.horizontal, 20)
            .padding(.bottom, 24)
        } else {
            NavigationLink {
                HealthView()
            } label: {
                HairlineCard {
                    HStack(spacing: 16) {
                        Image(systemName: "heart")
                            .font(.system(size: 24))
                            .foregroundStyle(.ink3)
                            .frame(width: 76, height: 76)
                            .overlay(Circle().strokeBorder(Color.hairline, style: StrokeStyle(lineWidth: 1, dash: [4])))
                        VStack(alignment: .leading, spacing: 2) {
                            Text("Readiness").kicker()
                            Text("Connect a wearable").font(.headline).foregroundStyle(.ink)
                            Text("Sync sleep + HRV in Health to score your day →")
                                .font(.caption).foregroundStyle(.ink2)
                                .fixedSize(horizontal: false, vertical: true)
                        }
                        Spacer()
                    }
                }
            }
            .buttonStyle(.plain)
            .padding(.horizontal, 20)
            .padding(.bottom, 24)
        }
    }

    // MARK: Today's session card (active program rotation slot)

    @ViewBuilder
    private var sessionCard: some View {
        if store.activeProgram == nil {
            noActiveProgram
        } else if let slot = store.todaySlot {
            if slot.isRestDay {
                restSlot
            } else {
                trainingSlot(slot)
            }
        } else {
            emptyProgram
        }
    }

    private func trainingSlot(_ slot: MockData.ProgramDay) -> some View {
        VStack(alignment: .leading, spacing: 0) {
            Rectangle().fill(Color.ink).frame(height: 2)
            HStack {
                Text(sessionKicker).kicker()
                Spacer()
                if let cycle = store.microcycleLabel {
                    Text(cycle)
                        .font(.system(size: 10, weight: .semibold))
                        .textCase(.uppercase).tracking(1.0)
                        .foregroundStyle(.ink3)
                }
            }
            .padding(.top, 14)
            Text(slot.name)
                .font(.system(size: 34, weight: .medium, design: .serif))
                .foregroundStyle(.ink)
                .padding(.top, 8)
            HStack(spacing: 16) {
                metaStat("\(slot.exercises.count)", "exercises")
                if store.todayEstimatedMinutes > 0 {
                    metaStat("~\(store.todayEstimatedMinutes)", "min")
                }
                if store.todaySetCount > 0 {
                    metaStat("\(store.todaySetCount)", "sets")
                }
                if store.inDeload {
                    Text("Deload")
                        .font(.system(size: 10, weight: .semibold))
                        .textCase(.uppercase).tracking(1.0)
                        .foregroundStyle(.warning)
                        .padding(.horizontal, 9)
                        .frame(height: 22)
                        .overlay(Capsule().stroke(Color.warning.opacity(0.45), lineWidth: 1))
                }
            }
            .padding(.top, 10)
            Button { startSession() } label: {
                Label(store.isStartingSession ? "Starting…" : "Start workout", systemImage: "play.fill")
            }
            .buttonStyle(.editorialPrimary)
            .disabled(store.isStartingSession)
            .padding(.top, 16)
        }
        .padding(.horizontal, 20)
        .padding(.bottom, 24)
    }

    private var restSlot: some View {
        VStack(alignment: .leading, spacing: 0) {
            HairlineCard {
                VStack(alignment: .leading, spacing: 0) {
                    Text("Today · Rest").kicker()
                    Text("Rest day")
                        .font(.titleSerif).italic().foregroundStyle(.ink2)
                        .padding(.top, 4)
                    if let next = store.nextTrainingName {
                        Text("Recover today. Next up: \(next).")
                            .font(.footnote).foregroundStyle(.ink2)
                            .fixedSize(horizontal: false, vertical: true)
                            .padding(.top, 4)
                    } else {
                        Text("Recover today — no session planned.")
                            .font(.footnote).foregroundStyle(.ink2)
                            .padding(.top, 4)
                    }
                }
            }
        }
        .padding(.horizontal, 20)
        .padding(.bottom, 24)
    }

    private var noActiveProgram: some View {
        VStack(alignment: .leading, spacing: 0) {
            HairlineCard {
                VStack(alignment: .leading, spacing: 0) {
                    Text("Today").kicker()
                    Text("No active program")
                        .font(.titleSerif).foregroundStyle(.ink)
                        .padding(.top, 4)
                    Text("Pick a program to get a session here every day. The active program drives your rotation.")
                        .font(.footnote).foregroundStyle(.ink2)
                        .fixedSize(horizontal: false, vertical: true)
                        .padding(.top, 6)
                    NavigationLink {
                        ProgramsRootView()
                    } label: {
                        Label("Pick a program", systemImage: "arrow.right")
                    }
                    .buttonStyle(.editorialSecondary)
                    .padding(.top, 14)
                }
            }
        }
        .padding(.horizontal, 20)
        .padding(.bottom, 24)
    }

    private var emptyProgram: some View {
        VStack(alignment: .leading, spacing: 0) {
            HairlineCard {
                VStack(alignment: .leading, spacing: 0) {
                    Text("Today").kicker()
                    Text(store.activeProgram?.name ?? "Your program")
                        .font(.titleSerif).foregroundStyle(.ink)
                        .padding(.top, 4)
                    Text("This program has no slots yet. Add training days in the builder.")
                        .font(.footnote).foregroundStyle(.ink2)
                        .fixedSize(horizontal: false, vertical: true)
                        .padding(.top, 6)
                    NavigationLink {
                        ProgramsRootView()
                    } label: {
                        Label("Open builder", systemImage: "arrow.right")
                    }
                    .buttonStyle(.editorialSecondary)
                    .padding(.top, 14)
                }
            }
        }
        .padding(.horizontal, 20)
        .padding(.bottom, 24)
    }

    private var sessionKicker: String {
        if let name = store.activeProgram?.name { return "Today · \(name)" }
        return "Today"
    }

    private func metaStat(_ value: String, _ label: String) -> some View {
        HStack(spacing: 4) {
            Text(value).font(.system(size: 13, weight: .semibold)).monospacedDigit().foregroundStyle(.ink)
            Text(label).font(.footnote).foregroundStyle(.ink2)
        }
    }

    // MARK: Quick meal-log

    private var quickMealLog: some View {
        HairlineCard {
            HStack(spacing: 16) {
                ZStack {
                    ActivityRing(value: store.nutritionFraction, size: 76, lineWidth: 6)
                    VStack(spacing: 0) {
                        Text(store.nutritionKcal.formatted())
                            .font(.figureSmall).monospacedDigit().foregroundStyle(.ink)
                        if let target = store.nutritionTargetKcal {
                            Text("/ \(target.formatted())").font(.caption2).foregroundStyle(.ink2)
                        }
                    }
                }
                VStack(alignment: .leading, spacing: 2) {
                    Text("Nutrition · today").kicker()
                    if let remaining = store.nutritionRemaining {
                        Text("\(remaining.formatted()) kcal remaining")
                            .font(.headline).foregroundStyle(.ink)
                    } else {
                        Text("\(store.nutritionKcal.formatted()) kcal logged")
                            .font(.headline).foregroundStyle(.ink)
                    }
                    HStack(spacing: 12) {
                        macroInline("\(store.nutritionProtein)", "P")
                        macroInline("\(store.nutritionCarbs)", "C")
                        macroInline("\(store.nutritionFat)", "F")
                    }
                    .padding(.top, 6)
                    NavigationLink {
                        NutritionView()
                    } label: {
                        Text("Open log →").font(.caption).fontWeight(.semibold).foregroundStyle(accent)
                    }
                    .buttonStyle(.plain)
                    .padding(.top, 6)
                }
                Spacer()
            }
        }
        .padding(.horizontal, 20)
        .padding(.bottom, 24)
    }

    private func macroInline(_ value: String, _ label: String) -> some View {
        HStack(spacing: 3) {
            Text(value).font(.caption).fontWeight(.semibold).monospacedDigit().foregroundStyle(.ink)
            Text(label).font(.caption).foregroundStyle(.ink2)
        }
    }

    // MARK: Insights feed

    @ViewBuilder
    private var insightsFeed: some View {
        if !store.insights.isEmpty {
            VStack(alignment: .leading, spacing: 14) {
                SectionHeaderLarge(title: "Insights", trailing: "View all")
                VStack(spacing: 0) {
                    ForEach(store.insights) { insight in
                        insightRow(insight)
                    }
                }
            }
            .padding(.horizontal, 20)
        }
    }

    private func insightRow(_ insight: APIInsight) -> some View {
        NavigationLink {
            InsightsView()
        } label: {
            HStack(alignment: .top, spacing: 12) {
                Rectangle()
                    .fill(severityColor(insight.severity))
                    .frame(width: 3)
                    .frame(maxHeight: .infinity)
                VStack(alignment: .leading, spacing: 4) {
                    Text(kindLabel(insight.kind))
                        .font(.system(size: 10, weight: .semibold))
                        .textCase(.uppercase).tracking(1.0)
                        .foregroundStyle(.ink3)
                    Text(insight.title).font(.headline).foregroundStyle(.ink)
                    if let body = insight.displayBody {
                        Text(body)
                            .font(.footnote).foregroundStyle(.ink2)
                            .lineLimit(2)
                            .fixedSize(horizontal: false, vertical: true)
                    }
                }
                Spacer(minLength: 8)
                Image(systemName: "arrow.right")
                    .font(.system(size: 13, weight: .semibold))
                    .foregroundStyle(.ink3)
                    .padding(.top, 4)
            }
            .padding(.vertical, 12)
            .contentShape(Rectangle())
            .overlay(alignment: .bottom) { Divider().overlay(Color.hairline) }
        }
        .buttonStyle(.plain)
        .fixedSize(horizontal: false, vertical: true)
    }

    private func severityColor(_ severity: String) -> Color {
        switch severity {
        case "info": return .success
        case "warn": return .warning
        case "action": return accent
        default: return .hairline
        }
    }

    private func kindLabel(_ kind: String) -> String {
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

    // MARK: Actions

    private func startSession() {
        Task {
            if let id = await store.startSession() {
                startedSessionID = id
                showingActiveSession = true
            }
        }
    }
}

#Preview {
    TodayView()
        .environment(TodayStore(preview: true))
        .environment(\.editorialAccent, AccentChoice.clay.color(for: .light))
}
