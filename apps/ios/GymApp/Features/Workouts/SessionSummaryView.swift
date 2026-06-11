//
//  SessionSummaryView.swift
//  GymApp
//
//  Post-workout summary: PR banner, stat tiles, per-muscle volume bars, set
//  list, next-session recs. Mirrors ScreenSummaryIOS.
//

import SwiftUI

struct SessionSummaryView: View {
    @Environment(\.editorialAccent) private var accent
    private let summary = MockData.sessionSummary
    private let statColumns = Array(repeating: GridItem(.flexible(), spacing: 8), count: 2)

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 18) {
                prBanner
                statTiles
                volumeSection
                setsSection
                recsSection
            }
            .padding(.bottom, 32)
            .padding(.top, 4)
        }
        .background(Color.bg)
        .scrollIndicators(.hidden)
        .navigationTitle("Summary")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Button { } label: { Image(systemName: "square.and.arrow.up") }
            }
        }
    }

    // MARK: PR banner

    private var prBanner: some View {
        VStack(alignment: .leading, spacing: 0) {
            Rectangle().fill(Color.ink).frame(height: 2)
            HStack(spacing: 8) {
                Image(systemName: "star.fill").font(.system(size: 14))
                Text(summary.prKicker).kicker().foregroundStyle(accent)
            }
            .foregroundStyle(accent)
            .padding(.top, 14)
            Text(summary.headline)
                .font(.system(size: 30, weight: .medium, design: .serif))
                .foregroundStyle(.ink)
                .padding(.top, 8)
            Text(summary.prDetail).font(.footnote).foregroundStyle(.ink2).padding(.top, 8)
        }
        .padding(.horizontal, 20)
    }

    // MARK: Stat tiles

    private var statTiles: some View {
        LazyVGrid(columns: statColumns, spacing: 8) {
            ForEach(summary.stats) { stat in
                StatTile(label: stat.label, value: stat.value, unit: stat.unit, delta: stat.delta)
            }
        }
        .padding(.horizontal, 20)
    }

    // MARK: Volume by muscle

    private var volumeSection: some View {
        VStack(alignment: .leading, spacing: 14) {
            SectionHeaderLarge(title: "Volume by muscle", trailing: "vs typical")
            EditorialCard {
                VStack(spacing: 0) {
                    ForEach(summary.muscles) { muscle in
                        muscleRow(muscle)
                    }
                }
            }
        }
        .padding(.horizontal, 20)
    }

    private func muscleRow(_ muscle: MockData.SummaryMuscle) -> some View {
        HStack(spacing: 10) {
            Text(muscle.name).font(.subheadline).foregroundStyle(.ink)
                .frame(width: 90, alignment: .leading)
            GeometryReader { geo in
                ZStack(alignment: .leading) {
                    Capsule().fill(Color.fill)
                    Capsule()
                        .fill(muscle.short ? Color.warning : accent)
                        .frame(width: geo.size.width * muscle.fraction)
                    // target marker
                    let markerX = geo.size.width * muscle.fraction
                        * (Double(muscle.target) / Double(muscle.sets))
                    Rectangle().fill(Color.ink3).frame(width: 2)
                        .offset(x: min(markerX, geo.size.width - 2))
                }
            }
            .frame(height: 6)
            Text("\(muscle.sets) / \(muscle.target)")
                .font(.caption).monospacedDigit().foregroundStyle(.ink2)
                .frame(width: 44, alignment: .trailing)
        }
        .padding(.vertical, 6)
    }

    // MARK: Sets list

    private var setsSection: some View {
        VStack(alignment: .leading, spacing: 14) {
            SectionHeaderLarge(title: "Sets", trailing: "5 exercises · 21 sets")
            VStack(spacing: 0) {
                Rectangle().fill(Color.hairline).frame(height: 1)
                ForEach(summary.exercises) { ex in
                    NavigationLink(value: WorkoutsView.Route.exerciseDetail) {
                        HStack(alignment: .top) {
                            VStack(alignment: .leading, spacing: 4) {
                                Text(ex.name).font(.headline).foregroundStyle(.ink)
                                Text(ex.sets).font(.caption).monospacedDigit().foregroundStyle(.ink2)
                            }
                            Spacer(minLength: 8)
                            Image(systemName: "chevron.right")
                                .font(.system(size: 13, weight: .semibold)).foregroundStyle(.ink3)
                        }
                        .padding(.vertical, 12)
                    }
                    .buttonStyle(.plain)
                    Rectangle().fill(Color.hairline).frame(height: 1)
                }
            }
        }
        .padding(.horizontal, 20)
    }

    // MARK: Next-session recs

    private var recsSection: some View {
        VStack(alignment: .leading, spacing: 14) {
            SectionHeaderLarge(title: "Next Push A", trailing: "3 recs")
            VStack(spacing: 0) {
                Rectangle().fill(Color.hairline).frame(height: 1)
                ForEach(Array(summary.recs.enumerated()), id: \.element.id) { index, rec in
                    GroupedRow(
                        systemImage: rec.systemImage,
                        title: rec.title,
                        detail: rec.detail,
                        showsSeparator: index < summary.recs.count - 1
                    ) {
                        Image(systemName: "chevron.right")
                            .font(.system(size: 13, weight: .semibold)).foregroundStyle(.ink3)
                    }
                }
                Rectangle().fill(Color.hairline).frame(height: 1)
            }
        }
        .padding(.horizontal, 20)
    }
}

#Preview {
    NavigationStack {
        SessionSummaryView()
            .environment(\.editorialAccent, AccentChoice.clay.color(for: .light))
    }
}
