//
//  InsightsView.swift
//  GymApp
//
//  Insights tab: stat grid, per-muscle volume heat, tonnage trend (Swift
//  Charts), insight cards, progress-photo compare. Mirrors ScreenInsightsIOS.
//

import SwiftUI
import Charts

struct InsightsView: View {
    @State private var range = "4w"
    @Environment(\.editorialAccent) private var accent

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
    }

    // MARK: Stat grid

    private var statGrid: some View {
        LazyVGrid(columns: statColumns, spacing: 8) {
            ForEach(MockData.insightStats) { stat in
                StatTile(label: stat.label, value: stat.value, unit: stat.unit, delta: stat.delta)
            }
        }
        .padding(.horizontal, 20)
        .padding(.bottom, 24)
    }

    // MARK: Volume heat

    private var volumeHeat: some View {
        VStack(alignment: .leading, spacing: 14) {
            SectionHeaderLarge(title: "Volume by muscle", trailing: "7 days")
            HairlineCard(padding: 12) {
                VStack(spacing: 12) {
                    LazyVGrid(columns: heatColumns, spacing: 6) {
                        ForEach(MockData.muscleVolumes) { muscle in
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
                        Text("23,180")
                            .font(.system(size: 34, weight: .medium, design: .serif))
                            .monospacedDigit()
                            .foregroundStyle(.ink)
                        Text("kg / wk").font(.footnote).foregroundStyle(.ink2)
                    }
                    Text("↑ 6% vs prior 4 weeks")
                        .font(.caption).foregroundStyle(.success)
                        .padding(.bottom, 8)
                    chart
                }
            }
        }
        .padding(.horizontal, 20)
        .padding(.bottom, 24)
    }

    private var chart: some View {
        Chart(MockData.tonnageTrend) { point in
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

    // MARK: Insight cards

    private var insightCards: some View {
        VStack(alignment: .leading, spacing: 14) {
            SectionHeaderLarge(title: "This week", trailing: "\(MockData.insightCards.count) cards")
            VStack(alignment: .leading, spacing: 10) {
                ForEach(MockData.insightCards) { card in
                    HStack(alignment: .top, spacing: 14) {
                        Rectangle().fill(card.tone).frame(width: 2)
                        VStack(alignment: .leading, spacing: 4) {
                            Text(card.kind)
                                .font(.system(size: 11, weight: .semibold))
                                .textCase(.uppercase)
                                .tracking(1.0)
                                .foregroundStyle(card.tone)
                            Text(card.title).font(.headline).foregroundStyle(.ink)
                            Text(card.body).font(.footnote).foregroundStyle(.ink2)
                        }
                    }
                    .fixedSize(horizontal: false, vertical: true)
                }
            }
        }
        .padding(.horizontal, 20)
        .padding(.bottom, 24)
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
    InsightsView().environment(\.editorialAccent, AccentChoice.clay.color(for: .light))
}
