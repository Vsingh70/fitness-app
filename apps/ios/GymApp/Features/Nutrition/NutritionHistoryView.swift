//
//  NutritionHistoryView.swift
//  GymApp
//
//  Nutrition trends (Direction A §6). Day / Week underline toggle; the Week view
//  is the 7-bar chart vs a dashed target (under-target muted, today clay). Below,
//  a stat band: Avg/day, Avg protein, Days on target, Adherence — serif figures
//  on top hairline rules. Swift Charts (BarMark + dashed RuleMark).
//

import SwiftUI
import Charts

struct NutritionHistoryView: View {
    @Environment(\.editorialAccent) private var accent
    @State private var range = "week"
    private let target = MockData.kcalTarget

    /// Last 7 days for the week view (today = the final, low day).
    private var week: [MockData.DayTotal] {
        Array(MockData.nutritionHistory.suffix(7))
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 22) {
                UnderlineSegmented(
                    selection: $range,
                    options: [("day", "Day"), ("week", "Week")],
                    spacing: 24
                )
                .padding(.top, 8)

                SectionHeaderLarge(title: "Daily energy", trailing: range == "day" ? "Today" : "7 days")
                chart
                statBand
            }
            .padding(.horizontal, 20)
            .padding(.bottom, 24)
        }
        .background(Color.bg)
        .scrollIndicators(.hidden)
        .navigationTitle("Trends")
        .navigationBarTitleDisplayMode(.inline)
    }

    // MARK: Chart

    private var data: [MockData.DayTotal] {
        range == "day" ? Array(MockData.nutritionHistory.suffix(1)) : week
    }

    private var chart: some View {
        Chart {
            ForEach(Array(data.enumerated()), id: \.element.id) { index, day in
                BarMark(
                    x: .value("Day", day.label),
                    y: .value("kcal", day.kcal),
                    width: .fixed(range == "day" ? 40 : 16)
                )
                .foregroundStyle(barColor(day: day, isLast: index == data.count - 1))
                .cornerRadius(3)
            }
            RuleMark(y: .value("Target", target))
                .foregroundStyle(Color.ink3)
                .lineStyle(StrokeStyle(lineWidth: 1, dash: [4]))
                .annotation(position: .top, alignment: .trailing) {
                    Text("Target \(target.formatted())")
                        .font(.caption2).monospacedDigit().foregroundStyle(.ink3)
                }
        }
        .chartXAxis(.hidden)
        .chartYAxis {
            AxisMarks { _ in AxisGridLine().foregroundStyle(Color.hairline) }
        }
        .frame(height: 180)
    }

    /// Today = clay, over-target = warning ink, under-target = muted.
    private func barColor(day: MockData.DayTotal, isLast: Bool) -> Color {
        if isLast { return accent }
        return day.kcal <= target ? Color.ink.opacity(0.28) : Color.warning
    }

    // MARK: Stat band

    private var statBand: some View {
        VStack(spacing: 16) {
            HStack(spacing: 16) {
                stat(label: "Avg / day", value: "2,540", unit: "kcal")
                stat(label: "Avg protein", value: "186", unit: "g")
            }
            HStack(spacing: 16) {
                stat(label: "Days on target", value: "5/7")
                stat(label: "Adherence", value: "86", unit: "%")
            }
        }
    }

    private func stat(label: String, value: String, unit: String? = nil) -> some View {
        VStack(alignment: .leading, spacing: 0) {
            Rectangle().fill(Color.hairline).frame(height: 1)
            Text(label).kicker().padding(.top, 10)
            HStack(alignment: .firstTextBaseline, spacing: 3) {
                Text(value).font(.figure).monospacedDigit().foregroundStyle(.ink)
                if let unit {
                    Text(unit).font(.footnote).foregroundStyle(.ink2)
                }
            }
            .padding(.top, 6)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }
}

#Preview {
    NavigationStack {
        NutritionHistoryView().environment(\.editorialAccent, AccentChoice.clay.color(for: .light))
    }
}
