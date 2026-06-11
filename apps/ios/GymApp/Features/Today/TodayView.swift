//
//  TodayView.swift
//  GymApp
//
//  Today tab: Fitbit metric carousel, nutrition strip, scheduled-workout
//  feature block, recommendations, weekly stats. Mirrors ScreenTodayIOS.
//

import SwiftUI

struct TodayView: View {
    @Environment(\.editorialAccent) private var accent

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 0) {
                ScreenHeader(title: "Today", subtitle: MockData.todayLong) {
                    MonogramBadge(text: MockData.userInitials)
                }

                fitbitStrip
                metricCarousel
                nutritionStrip
                scheduledBlock
                recommendations
                weeklyStats
            }
            .padding(.bottom, 24)
        }
        .background(Color.bg)
        .scrollIndicators(.hidden)
    }

    // MARK: Fitbit sync line

    private var fitbitStrip: some View {
        HStack {
            HStack(spacing: 6) {
                Circle().fill(Color.success).frame(width: 6, height: 6)
                Text("Fitbit · synced 2m ago").font(.footnote).foregroundStyle(.ink2)
            }
            Spacer()
            Text("Hold to reorder").font(.caption).foregroundStyle(.ink3)
        }
        .padding(.horizontal, 20)
        .padding(.bottom, 6)
    }

    // MARK: Metric carousel

    private var metricCarousel: some View {
        ScrollView(.horizontal) {
            HStack(spacing: 10) {
                ForEach(MockData.healthMetrics) { metric in
                    metricTile(metric)
                        .frame(width: 142)
                }
            }
            .padding(.horizontal, 20)
        }
        .scrollIndicators(.hidden)
        .padding(.bottom, 24)
    }

    private func metricTile(_ metric: MockData.HealthMetric) -> some View {
        VStack(alignment: .leading, spacing: 0) {
            HStack {
                Image(systemName: metric.systemImage)
                    .font(.system(size: 15))
                    .foregroundStyle(.ink2)
                Spacer()
                if let ring = metric.ringValue {
                    ActivityRing(value: ring, size: 28, lineWidth: 3)
                }
            }
            Text(metric.label).kicker().padding(.top, 8)
            HStack(alignment: .firstTextBaseline, spacing: 2) {
                Text(metric.value).font(.figureSmall).monospacedDigit().foregroundStyle(.ink)
                if let unit = metric.unit {
                    Text(unit).font(.caption2).foregroundStyle(.ink2)
                }
            }
            .padding(.top, 2)
            Text(metric.sub)
                .font(.caption2)
                .foregroundStyle(metric.sub.contains("↑") || metric.sub.contains("↓") ? accent : .ink2)
                .padding(.top, 2)
        }
        .padding(14)
        .frame(maxHeight: .infinity, alignment: .top)
        .overlay(RoundedRectangle(cornerRadius: 3).stroke(Color.hairline, lineWidth: 1))
    }

    // MARK: Nutrition strip

    private var nutritionStrip: some View {
        HairlineCard {
            HStack(spacing: 16) {
                ZStack {
                    ActivityRing(value: 0.6, size: 76, lineWidth: 6)
                    VStack(spacing: 0) {
                        Text("1,620").font(.figureSmall).monospacedDigit().foregroundStyle(.ink)
                        Text("/ 2,680").font(.caption2).foregroundStyle(.ink2)
                    }
                }
                VStack(alignment: .leading, spacing: 2) {
                    Text("Nutrition · today").kicker()
                    Text("1,060 kcal remaining").font(.headline).foregroundStyle(.ink)
                    HStack(spacing: 12) {
                        macroInline("134", "P")
                        macroInline("168", "C")
                        macroInline("51", "F")
                    }
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

    // MARK: Scheduled workout feature block

    private var scheduledBlock: some View {
        let w = MockData.scheduledToday
        return VStack(alignment: .leading, spacing: 0) {
            Rectangle().fill(Color.ink).frame(height: 2)
            Text(w.kicker).kicker().padding(.top, 14)
            Text(w.headline)
                .font(.system(size: 34, weight: .medium, design: .serif))
                .foregroundStyle(.ink)
                .padding(.top, 8)
            HStack(spacing: 16) {
                metaStat("\(w.exercises)", "exercises")
                metaStat("~\(w.minutes)", "min")
                metaStat("\(w.sets)", "sets")
            }
            .padding(.top, 10)
            Button { } label: {
                Label("Start workout", systemImage: "play.fill")
            }
            .buttonStyle(.editorialPrimary)
            .padding(.top, 16)
        }
        .padding(.horizontal, 20)
        .padding(.bottom, 24)
    }

    private func metaStat(_ value: String, _ label: String) -> some View {
        HStack(spacing: 4) {
            Text(value).font(.system(size: 13, weight: .semibold)).monospacedDigit().foregroundStyle(.ink)
            Text(label).font(.footnote).foregroundStyle(.ink2)
        }
    }

    // MARK: Recommendations

    private var recommendations: some View {
        let rec = MockData.topRecommendation
        return VStack(alignment: .leading, spacing: 14) {
            SectionHeaderLarge(title: "Recommendations", trailing: "See all")
            HairlineCard {
                HStack(alignment: .top, spacing: 12) {
                    Image(systemName: "arrow.right")
                        .font(.system(size: 20))
                        .foregroundStyle(accent)
                        .padding(.top, 2)
                    VStack(alignment: .leading, spacing: 4) {
                        Text(rec.kicker)
                            .font(.system(size: 11, weight: .semibold))
                            .textCase(.uppercase)
                            .tracking(1.2)
                            .foregroundStyle(accent)
                        Text(rec.title).font(.headline).foregroundStyle(.ink)
                        Text(rec.rationale).font(.footnote).foregroundStyle(.ink2)
                        HStack(spacing: 4) {
                            ForEach(0..<3) { _ in
                                Circle().fill(accent).frame(width: 5, height: 5)
                            }
                            Text(rec.confidence).font(.caption2).foregroundStyle(.ink2)
                                .padding(.leading, 4)
                        }
                        .padding(.top, 4)
                    }
                    Spacer(minLength: 8)
                    Button(rec.cta) { }.buttonStyle(.editorialSmallTonal)
                }
            }
        }
        .padding(.horizontal, 20)
        .padding(.bottom, 24)
    }

    // MARK: Weekly stats

    private var weeklyStats: some View {
        VStack(alignment: .leading, spacing: 14) {
            SectionHeaderLarge(title: "This week", trailing: "Insights")
            HStack(spacing: 8) {
                ForEach(MockData.thisWeekStats) { stat in
                    StatTile(label: stat.label, value: stat.value, unit: stat.unit, delta: stat.delta)
                }
            }
        }
        .padding(.horizontal, 20)
    }
}

#Preview {
    TodayView().environment(\.editorialAccent, AccentChoice.clay.color(for: .light))
}
