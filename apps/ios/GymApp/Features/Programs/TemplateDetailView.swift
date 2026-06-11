//
//  TemplateDetailView.swift
//  GymApp
//
//  Read-only template detail (Direction A §6): serif hero, a spec strip
//  (weeks / per-week / goal / rating), a day-by-day breakdown, and a pinned
//  "Use this template" CTA that copies it to a new active program and returns
//  to the overview.
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
                hero(t)
                specStrip(t)
                ForEach(t.days) { day in
                    dayBlock(day, mode: .rpe)
                }
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
            } label: { Text("Use this template") }
                .buttonStyle(.editorialPrimary)
                .padding(.horizontal, 20)
                .padding(.vertical, 10)
                .background(.thinMaterial)
        }
    }

    private func hero(_ t: MockData.ProgramTemplate) -> some View {
        VStack(alignment: .leading, spacing: 0) {
            Text("\(t.category.rawValue.uppercased()) · \(t.weeks) WEEKS")
                .font(.system(size: 10, weight: .semibold)).tracking(1.2)
                .foregroundStyle(accent)
            Text(t.name)
                .font(.system(size: 30, weight: .medium, design: .serif))
                .foregroundStyle(.ink).padding(.top, 4)
                .fixedSize(horizontal: false, vertical: true)
            Text(t.description)
                .font(.footnote).foregroundStyle(.ink2).padding(.top, 8)
                .fixedSize(horizontal: false, vertical: true)
        }
        .padding(.horizontal, 24)
        .padding(.top, 8)
        .padding(.bottom, 20)
    }

    private func specStrip(_ t: MockData.ProgramTemplate) -> some View {
        HStack(spacing: 0) {
            specPair("\(t.weeks)", "weeks")
            Spacer()
            specPair("\(t.daysPerWeek)×", "per week")
            Spacer()
            specPair(t.goal, "goal")
            Spacer()
            specPair("★ \(t.rating)", "rating")
        }
        .padding(.horizontal, 24)
        .padding(.vertical, 16)
        .overlay(alignment: .top) { Divider().overlay(Color.hairline) }
        .overlay(alignment: .bottom) { Divider().overlay(Color.hairline) }
    }

    private func specPair(_ value: String, _ label: String) -> some View {
        VStack(alignment: .leading, spacing: 2) {
            Text(value).font(.figureSmall).monospacedDigit().foregroundStyle(.ink)
            Text(label).font(.caption2).foregroundStyle(.ink2)
        }
    }

    private func dayBlock(_ day: MockData.ProgramDay, mode: MockData.IntensityMode) -> some View {
        VStack(alignment: .leading, spacing: 0) {
            Text(day.name).font(.titleSerif).foregroundStyle(.ink)
                .padding(.bottom, 8)
            VStack(spacing: 0) {
                Rectangle().fill(Color.hairline).frame(height: 1)
                ForEach(Array(day.exercises.enumerated()), id: \.element.id) { index, ex in
                    HStack {
                        Text(ex.name).font(.bodyText).foregroundStyle(.ink)
                        Spacer(minLength: 8)
                        Text(MockData.schemeLine(ex, mode: mode))
                            .font(.caption).monospacedDigit().foregroundStyle(.ink2)
                    }
                    .frame(minHeight: 40)
                    .padding(.vertical, 4)
                    if index < day.exercises.count - 1 {
                        Rectangle().fill(Color.hairline).frame(height: 1)
                    }
                }
                Rectangle().fill(Color.hairline).frame(height: 1)
            }
        }
        .padding(.horizontal, 20)
        .padding(.top, 20)
    }
}

#Preview {
    NavigationStack {
        TemplateDetailView()
            .environment(ProgramsStore())
            .environment(\.editorialAccent, AccentChoice.clay.color(for: .light))
    }
}
