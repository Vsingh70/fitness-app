//
//  TemplateDetailView.swift
//  GymApp
//
//  Read-only template detail (Direction A §6 · design IosDetail / .pid-*):
//  serif hero over a 2px ink rule, a Weeks / Per-week / Rating spec strip, a
//  day-by-day breakdown, and a pinned "Use this template" CTA that copies it to
//  a new active program and returns to the overview.
//

import SwiftUI

struct TemplateDetailView: View {
    @Environment(\.editorialAccent) private var accent
    @Environment(ProgramsStore.self) private var store
    @Environment(\.programPopToOverview) private var popToOverview

    /// The detail shown — defaults to the marked (active) template, else first.
    private var template: MockData.ProgramTemplate {
        MockData.templates.first { $0.active } ?? MockData.templates[0]
    }

    var body: some View {
        let t = template
        ScrollView {
            VStack(alignment: .leading, spacing: 0) {
                // pi-head kicker
                Text("Templates ›")
                    .font(.system(size: 11, weight: .semibold)).textCase(.uppercase)
                    .tracking(1.6).foregroundStyle(.ink2)
                    .padding(.horizontal, 22).padding(.top, 10).padding(.bottom, 8)

                hero(t)
                    .padding(.horizontal, 22)

                VStack(alignment: .leading, spacing: 0) {
                    ForEach(Array(t.days.enumerated()), id: \.element.id) { index, day in
                        dayBlock(day, number: index + 1)
                    }
                }
                .padding(.horizontal, 22).padding(.top, 4)
            }
            .padding(.bottom, 24)
        }
        .background(Color.bg)
        .scrollIndicators(.hidden)
        .navigationTitle("")
        .navigationBarTitleDisplayMode(.inline)
        .safeAreaInset(edge: .bottom) {
            Button {
                store.adopt(t)
                popToOverview()
            } label: { Text("Use this template").frame(maxWidth: .infinity) }
                .buttonStyle(.editorialPrimary)
                .padding(.horizontal, 16)
                .padding(.vertical, 10)
                .background(.thinMaterial)
        }
    }

    // pid-hero
    private func hero(_ t: MockData.ProgramTemplate) -> some View {
        VStack(alignment: .leading, spacing: 0) {
            Text(t.category.rawValue.uppercased())
                .font(.system(size: 10, weight: .semibold)).tracking(1.4)
                .foregroundStyle(.ink3)
            Text(t.name)
                .font(.system(size: 26, weight: .medium, design: .serif))
                .foregroundStyle(.ink).padding(.top, 5).padding(.bottom, 7)
                .fixedSize(horizontal: false, vertical: true)
            Text(t.description)
                .font(.system(size: 13)).foregroundStyle(.ink2).lineSpacing(2)
                .fixedSize(horizontal: false, vertical: true)
            HStack(spacing: 22) {
                spec("\(t.microcycleLength)", "Slots")
                spec("\(t.mesocycleLengthMicrocycles)", "Cycles")
                spec("\(t.rating)★", "Rating")
            }
            .padding(.top, 14)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(.bottom, 14)
        .overlay(alignment: .bottom) { Rectangle().fill(Color.ink).frame(height: 2) }
    }

    private func spec(_ value: String, _ label: String) -> some View {
        VStack(alignment: .leading, spacing: 2) {
            Text(value)
                .font(.system(size: 16, weight: .medium, design: .serif))
                .monospacedDigit().foregroundStyle(.ink)
            Text(label)
                .font(.system(size: 9, weight: .semibold)).textCase(.uppercase)
                .tracking(0.9).foregroundStyle(.ink3)
        }
    }

    // pid-day
    private func dayBlock(_ day: MockData.ProgramDay, number: Int) -> some View {
        VStack(alignment: .leading, spacing: 0) {
            Text("Day \(number)")
                .font(.system(size: 9, weight: .semibold)).textCase(.uppercase)
                .tracking(0.9).foregroundStyle(.ink3)
            Text(day.name)
                .font(.system(size: 16, weight: .medium, design: .serif))
                .foregroundStyle(.ink).padding(.top, 2).padding(.bottom, 4)
            ForEach(day.exercises) { ex in
                HStack {
                    Text(ex.name).font(.system(size: 11)).foregroundStyle(.ink2)
                    Spacer(minLength: 8)
                    Text("\(ex.sets)×\(ex.reps)")
                        .font(.system(size: 11, design: .serif))
                        .monospacedDigit().foregroundStyle(.ink3)
                }
                .padding(.vertical, 3)
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(.vertical, 13)
        .overlay(alignment: .bottom) { Rectangle().fill(Color.hairline).frame(height: 1) }
    }
}

#Preview {
    NavigationStack {
        TemplateDetailView()
            .environment(ProgramsStore())
            .environment(\.editorialAccent, AccentChoice.clay.color(for: .light))
    }
}
