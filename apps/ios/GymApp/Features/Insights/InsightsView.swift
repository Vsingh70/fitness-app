//
//  InsightsView.swift
//  GymApp
//
//  Insights tab: stat grid, per-muscle volume heat, tonnage trend (Swift
//  Charts), insight cards, progress-photo compare. Mirrors the shipped web
//  `/analytics` (Insights) page. Live data comes from `InsightsStore`; the
//  progress-photo compare stays static (no photo API yet).
//

import SwiftUI
import Charts

struct InsightsView: View {
    @Environment(InsightsStore.self) private var store
    @Environment(AppNavigator.self) private var navigator
    @Environment(\.editorialAccent) private var accent
    @State private var range = "4w"

    private let heatColumns = Array(repeating: GridItem(.flexible(), spacing: 6), count: 4)
    private let statColumns = Array(repeating: GridItem(.flexible(), spacing: 8), count: 2)

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 0) {
                ScreenHeader(title: "Insights") {
                    UnderlineSegmented(
                        selection: $range,
                        options: [("1w", "1w"), ("4w", "4w"), ("3m", "3m")]
                    )
                    .fixedSize()
                }
                if case .failed(let message) = store.loadState {
                    errorBanner(message)
                }
                statGrid
                volumeHeat
                tonnageTrend
                insightCards
                progressPhotos
            }
            .padding(.bottom, 24)
        }
        .background(Color.bg)
        .scrollIndicators(.hidden)
        .refreshable { await store.load() }
    }

    // MARK: Error banner

    private func errorBanner(_ message: String) -> some View {
        HStack(spacing: 10) {
            Text(message).font(.footnote).foregroundStyle(.ink2)
            Spacer()
            Button("Retry") { Task { await store.load() } }
                .font(.footnote.weight(.semibold))
                .foregroundStyle(accent)
        }
        .padding(.horizontal, 20)
        .padding(.bottom, 16)
    }

    // MARK: Stat grid

    private var statGrid: some View {
        LazyVGrid(columns: statColumns, spacing: 8) {
            ForEach(store.stats) { stat in
                StatTile(label: stat.label, value: stat.value, unit: stat.unit, delta: stat.delta)
            }
        }
        .padding(.horizontal, 20)
        .padding(.bottom, 24)
    }

    // MARK: Volume heat

    private var volumeHeat: some View {
        VStack(alignment: .leading, spacing: 14) {
            SectionHeaderLarge(title: "Volume by muscle", trailing: "This week")
            HairlineCard(padding: 12) {
                VStack(spacing: 12) {
                    LazyVGrid(columns: heatColumns, spacing: 6) {
                        ForEach(store.muscleVolumes) { muscle in
                            heatCell(muscle)
                        }
                    }
                    legend
                }
            }
        }
        .padding(.horizontal, 20)
        .padding(.bottom, 24)
    }

    private func heatCell(_ muscle: MockData.MuscleVolume) -> some View {
        let level = muscle.level
        let bg = level == 0 ? Color.fill : accent.opacity(MockData.heatOpacity(level))
        let fg: Color = level >= 3 ? .bg : .ink
        return VStack(alignment: .leading, spacing: 1) {
            Text(muscle.name)
                .font(.system(size: 10, weight: .regular))
                .textCase(.uppercase)
                .tracking(0.6)
                .foregroundStyle(fg.opacity(0.78))
                .lineLimit(1)
            Text("\(muscle.sets)")
                .font(.figureSmall)
                .monospacedDigit()
                .foregroundStyle(fg)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(.horizontal, 10)
        .padding(.vertical, 9)
        .background(RoundedRectangle(cornerRadius: 3).fill(bg))
    }

    private var legend: some View {
        HStack {
            Text("Tile = sets vs target").font(.caption2).foregroundStyle(.ink2)
            Spacer()
            HStack(spacing: 4) {
                Text("Less").font(.caption2).foregroundStyle(.ink2)
                ForEach(0..<5) { level in
                    RoundedRectangle(cornerRadius: 3)
                        .fill(level == 0 ? Color.fill : accent.opacity(MockData.heatOpacity(level)))
                        .frame(width: 12, height: 12)
                }
                Text("More").font(.caption2).foregroundStyle(.ink2)
            }
        }
        .padding(.horizontal, 4)
    }

    // MARK: Tonnage trend

    private var tonnageTrend: some View {
        VStack(alignment: .leading, spacing: 14) {
            SectionHeaderLarge(title: "Tonnage trend", trailing: "8 weeks")
            HairlineCard {
                VStack(alignment: .leading, spacing: 0) {
                    HStack(alignment: .firstTextBaseline, spacing: 6) {
                        Text(Int(store.weeklyTonnage).formatted(.number.grouping(.automatic)))
                            .font(.system(size: 34, weight: .medium, design: .serif))
                            .monospacedDigit()
                            .foregroundStyle(.ink)
                        Text("kg / wk").font(.footnote).foregroundStyle(.ink2)
                    }
                    if let delta = store.tonnageDeltaText {
                        Text(delta)
                            .font(.caption).foregroundStyle(.success)
                            .padding(.bottom, 8)
                    } else {
                        Color.clear.frame(height: 8)
                    }
                    chart
                }
            }
        }
        .padding(.horizontal, 20)
        .padding(.bottom, 24)
    }

    @ViewBuilder
    private var chart: some View {
        if store.tonnageTrend.isEmpty {
            Text("Log a few sessions to see your tonnage trend.")
                .font(.footnote).foregroundStyle(.ink2)
                .frame(maxWidth: .infinity, minHeight: 100, alignment: .center)
        } else {
            Chart(store.tonnageTrend) { point in
                AreaMark(
                    x: .value("Week", point.week),
                    y: .value("Tonnage", point.kg)
                )
                .foregroundStyle(
                    .linearGradient(
                        colors: [accent.opacity(0.25), accent.opacity(0)],
                        startPoint: .top, endPoint: .bottom
                    )
                )
                LineMark(
                    x: .value("Week", point.week),
                    y: .value("Tonnage", point.kg)
                )
                .foregroundStyle(accent)
                .lineStyle(StrokeStyle(lineWidth: 1.6, lineCap: .round, lineJoin: .round))
            }
            .chartXAxis(.hidden)
            .chartYAxis(.hidden)
            .frame(height: 100)
        }
    }

    // MARK: Insight cards

    private var insightCards: some View {
        VStack(alignment: .leading, spacing: 14) {
            SectionHeaderLarge(
                title: "This week",
                trailing: "\(store.cards.count) \(store.cards.count == 1 ? "card" : "cards")"
            )
            if store.cards.isEmpty {
                Text("No active insights. Log a few more sessions and check back.")
                    .font(.footnote).foregroundStyle(.ink2)
            } else {
                VStack(alignment: .leading, spacing: 10) {
                    ForEach(store.cards) { card in
                        insightCard(card)
                    }
                }
            }
        }
        .padding(.horizontal, 20)
        .padding(.bottom, 24)
    }

    private func insightCard(_ card: InsightCardVM) -> some View {
        HStack(alignment: .top, spacing: 14) {
            Rectangle().fill(card.tone).frame(width: 2)
            VStack(alignment: .leading, spacing: 4) {
                Text(card.kindLabel)
                    .font(.system(size: 11, weight: .semibold))
                    .textCase(.uppercase)
                    .tracking(1.0)
                    .foregroundStyle(card.tone)
                Text(card.title).font(.headline).foregroundStyle(.ink)
                if let body = card.body {
                    Text(body).font(.footnote).foregroundStyle(.ink2)
                }
                if let label = card.ctaLabel {
                    Button { deepLink(card.destination) } label: {
                        HStack(spacing: 4) {
                            Text(label)
                            Image(systemName: "arrow.right")
                        }
                        .font(.system(size: 13, weight: .semibold))
                        .foregroundStyle(.ink)
                    }
                    .buttonStyle(.plain)
                    .padding(.top, 4)
                }
            }
        }
        .fixedSize(horizontal: false, vertical: true)
    }

    private func deepLink(_ destination: InsightCardVM.Destination) {
        switch destination {
        case .exercise:
            // The exercise analytics screen lives in the Workouts tab's stack.
            navigator.openExercise()
        case .programs:
            navigator.openPrograms()
        case .none:
            break
        }
    }

    // MARK: Progress photos

    private var progressPhotos: some View {
        VStack(alignment: .leading, spacing: 14) {
            SectionHeaderLarge(title: "Progress photos", trailing: "Compare")
            HairlineCard(padding: 12) {
                VStack(spacing: 12) {
                    HStack(spacing: 10) {
                        photoPlaceholder(caption: "13 weeks ago")
                        Image(systemName: "arrow.right")
                            .font(.system(size: 18))
                            .foregroundStyle(.ink3)
                        photoPlaceholder(caption: "Today")
                    }
                    HStack {
                        Text("Bodyweight").font(.caption).foregroundStyle(.ink2)
                        Spacer()
                        Text("−3.8 kg · ↓ 4.6%")
                            .font(.caption).monospacedDigit().foregroundStyle(.success)
                    }
                    .padding(.horizontal, 4)
                }
            }
        }
        .padding(.horizontal, 20)
    }

    private func photoPlaceholder(caption: String) -> some View {
        VStack(spacing: 6) {
            Text("FRONT").font(.system(size: 9, weight: .semibold)).tracking(1.0)
            Text(caption.uppercased()).font(.system(size: 10, weight: .semibold)).tracking(1.0)
        }
        .foregroundStyle(.ink2)
        .frame(maxWidth: .infinity)
        .aspectRatio(3.0 / 4.0, contentMode: .fit)
        .background(RoundedRectangle(cornerRadius: 2).fill(Color.fill))
        .overlay(RoundedRectangle(cornerRadius: 2).stroke(Color.hairline, lineWidth: 1))
    }
}

#Preview {
    InsightsView()
        .environment(InsightsStore(preview: true))
        .environment(AppNavigator())
        .environment(\.editorialAccent, AccentChoice.clay.color(for: .light))
}
