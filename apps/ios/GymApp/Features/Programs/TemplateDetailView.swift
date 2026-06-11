//
//  TemplateDetailView.swift
//  GymApp
//
//  Read-only template preview, week by week, with a "Use this program" CTA.
//  Designed to the editorial system + 08.03 spec (no prototype frame).
//

import SwiftUI

struct TemplateDetailView: View {
    @Environment(\.editorialAccent) private var accent

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 0) {
                hero
                ForEach(MockData.sampleWeek) { day in
                    dayBlock(day)
                }
            }
            .padding(.bottom, 24)
        }
        .background(Color.bg)
        .scrollIndicators(.hidden)
        .navigationTitle("")
        .navigationBarTitleDisplayMode(.inline)
        .safeAreaInset(edge: .bottom) {
            Button { } label: { Text("Use this program") }
                .buttonStyle(.editorialPrimary)
                .padding(.horizontal, 20)
                .padding(.vertical, 10)
                .background(.thinMaterial)
        }
    }

    private var hero: some View {
        VStack(alignment: .leading, spacing: 0) {
            Text("HYPERTROPHY · 8 WEEKS")
                .font(.system(size: 10, weight: .semibold)).tracking(1.2)
                .foregroundStyle(accent)
            Text("PPL — Vanilla 6-day")
                .font(.system(size: 30, weight: .medium, design: .serif))
                .foregroundStyle(.ink).padding(.top, 4)
            Text("Push / Pull / Legs, six days a week. Double-progression on compounds.")
                .font(.footnote).foregroundStyle(.ink2).padding(.top, 8)
        }
        .padding(.horizontal, 24)
        .padding(.top, 8)
        .padding(.bottom, 20)
        .overlay(alignment: .bottom) { Divider().overlay(Color.hairline) }
    }

    private func dayBlock(_ day: MockData.ProgramDay) -> some View {
        VStack(alignment: .leading, spacing: 0) {
            Text(day.name).font(.titleSerif).foregroundStyle(.ink)
                .padding(.bottom, 8)
            VStack(spacing: 0) {
                Rectangle().fill(Color.hairline).frame(height: 1)
                ForEach(Array(day.exercises.enumerated()), id: \.element.id) { index, ex in
                    HStack {
                        Text(ex.name).font(.bodyText).foregroundStyle(.ink)
                        Spacer(minLength: 8)
                        Text(ex.target).font(.caption).monospacedDigit().foregroundStyle(.ink2)
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
        TemplateDetailView().environment(\.editorialAccent, AccentChoice.clay.color(for: .light))
    }
}
