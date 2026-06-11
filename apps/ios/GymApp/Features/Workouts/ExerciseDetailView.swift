//
//  ExerciseDetailView.swift
//  GymApp
//
//  Per-exercise analytics: PR tiles, recommendation strip, underline tabs,
//  e1RM trend + working-set volume charts. Mirrors ScreenExerciseIOS.
//

import SwiftUI
import Charts

struct ExerciseDetailView: View {
    @Environment(\.editorialAccent) private var accent
    @State private var tab = "Trends"

    private let detail = MockData.exerciseDetail
    private let statColumns = Array(repeating: GridItem(.flexible(), spacing: 8), count: 2)

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 0) {
                hero
                prTiles
                recStrip
                tabs
                e1rmCard
                volumeCard
                startButton
            }
            .padding(.bottom, 32)
        }
        .background(Color.bg)
        .scrollIndicators(.hidden)
        .navigationTitle("")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Button { } label: { Image(systemName: "plus") }
            }
        }
    }

    // MARK: Hero

    private var hero: some View {
        VStack(alignment: .leading, spacing: 0) {
            Text(detail.kicker)
                .font(.system(size: 12, weight: .semibold))
                .textCase(.uppercase)
                .tracking(0.7)
                .foregroundStyle(accent)
            Text(detail.name)
                .font(.system(size: 30, weight: .medium, design: .serif))
                .foregroundStyle(.ink)
                .padding(.top, 4)
            HStack(spacing: 14) {
                ForEach(Array(detail.muscles.enumerated()), id: \.offset) { _, m in
                    EditorialChip(text: m.0, tone: m.1 ? accent : .ink2)
                }
            }
            .padding(.top, 10)
        }
        .padding(.horizontal, 24)
        .padding(.bottom, 20)
        .overlay(alignment: .bottom) { Divider().overlay(Color.hairline) }
    }

    // MARK: PR tiles

    private var prTiles: some View {
        LazyVGrid(columns: statColumns, spacing: 8) {
            ForEach(detail.stats) { stat in
                StatTile(label: stat.label, value: stat.value, unit: stat.unit, delta: stat.delta)
            }
        }
        .padding(.horizontal, 20)
        .padding(.top, 18)
        .padding(.bottom, 18)
    }

    // MARK: Recommendation strip

    private var recStrip: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(detail.recTitle).font(.headline).foregroundStyle(accent)
            Text(detail.recBody).font(.footnote).foregroundStyle(.ink2)
            Button("Apply to today") { }
                .buttonStyle(.editorialSmallTonal)
                .padding(.top, 6)
        }
        .padding(14)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(RoundedRectangle(cornerRadius: 4).fill(accent.opacity(0.10)))
        .overlay(RoundedRectangle(cornerRadius: 4).stroke(Color.hairline, lineWidth: 1))
        .padding(.horizontal, 20)
        .padding(.bottom, 18)
    }

    // MARK: Tabs

    private var tabs: some View {
        UnderlineSegmented(
            selection: $tab,
            options: [("Trends", "Trends"), ("Sets", "Sets"),
                      ("Variants", "Variants"), ("Notes", "Notes")],
            spacing: 24
        )
        .padding(.horizontal, 20)
        .padding(.bottom, 16)
    }

    // MARK: e1RM card

    private var e1rmCard: some View {
        EditorialCard {
            VStack(alignment: .leading, spacing: 0) {
                Text("Estimated 1RM · 6 months")
                    .font(.caption).fontWeight(.semibold).foregroundStyle(.ink2)
                HStack(alignment: .firstTextBaseline, spacing: 4) {
                    Text(detail.e1rmCurrent)
                        .font(.system(size: 28, weight: .medium, design: .serif))
                        .monospacedDigit().foregroundStyle(.ink)
                    Text("kg").font(.footnote).foregroundStyle(.ink2)
                }
                .padding(.top, 2)
                Text(detail.e1rmDelta).font(.footnote).foregroundStyle(.success)

                Chart {
                    ForEach(detail.e1rmTrend) { point in
                        AreaMark(x: .value("Month", point.month), y: .value("e1RM", point.value))
                            .foregroundStyle(.linearGradient(
                                colors: [accent.opacity(0.30), accent.opacity(0)],
                                startPoint: .top, endPoint: .bottom))
                        LineMark(x: .value("Month", point.month), y: .value("e1RM", point.value))
                            .foregroundStyle(accent)
                            .lineStyle(StrokeStyle(lineWidth: 2.4, lineCap: .round, lineJoin: .round))
                    }
                    if let last = detail.e1rmTrend.last {
                        PointMark(x: .value("Month", last.month), y: .value("e1RM", last.value))
                            .foregroundStyle(accent)
                            .symbolSize(60)
                    }
                }
                .chartYAxis { AxisMarks { _ in AxisGridLine().foregroundStyle(Color.hairline) } }
                .chartXAxis {
                    AxisMarks { value in
                        AxisValueLabel {
                            if let m = value.as(String.self) {
                                Text(m.uppercased())
                                    .font(.system(size: 11, design: .monospaced))
                                    .foregroundStyle(.ink3)
                            }
                        }
                    }
                }
                .frame(height: 140)
                .padding(.top, 12)
            }
        }
        .padding(.horizontal, 20)
        .padding(.bottom, 18)
    }

    // MARK: Volume card

    private var volumeCard: some View {
        EditorialCard {
            VStack(alignment: .leading, spacing: 10) {
                Text("Working set volume · last 11 sessions")
                    .font(.caption).fontWeight(.semibold).foregroundStyle(.ink2)
                Chart(detail.volumeBars) { bar in
                    BarMark(
                        x: .value("Session", bar.session),
                        y: .value("Volume", bar.value),
                        width: .fixed(14)
                    )
                    .foregroundStyle(bar.isPR ? Color.pr : accent.opacity(0.7))
                    .cornerRadius(3)
                }
                .chartXAxis(.hidden)
                .chartYAxis(.hidden)
                .frame(height: 100)
            }
        }
        .padding(.horizontal, 20)
        .padding(.bottom, 18)
    }

    // MARK: Start button

    private var startButton: some View {
        Button { } label: {
            Label("Start session with bench", systemImage: "play.fill")
        }
        .buttonStyle(.editorialPrimary)
        .padding(.horizontal, 20)
    }
}

#Preview {
    NavigationStack {
        ExerciseDetailView()
            .environment(\.editorialAccent, AccentChoice.clay.color(for: .light))
    }
}
