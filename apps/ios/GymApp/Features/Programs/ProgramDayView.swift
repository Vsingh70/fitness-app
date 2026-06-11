//
//  ProgramDayView.swift
//  GymApp
//
//  Per-day detail (Direction A §6): day hero (Day n · split · week), each
//  exercise with a Sets / Reps / {RPE|RIR} / Rest scheme row and a
//  "Progression — …" line, plus a Start workout action.
//

import SwiftUI

struct ProgramDayView: View {
    @Environment(\.editorialAccent) private var accent
    @Environment(\.programsStore) private var store
    @Environment(\.programNavigate) private var navigate

    let dayIndex: Int

    private var program: MockData.Program { store.active ?? MockData.myPrograms[0] }
    private var day: MockData.ProgramDay {
        let days = program.days
        guard days.indices.contains(dayIndex) else { return MockData.pplDays[0] }
        return days[dayIndex]
    }

    /// Suggested rest by position — compounds get longer rests.
    private let rests = ["3:00", "2:30", "2:00", "1:30", "1:30", "1:30"]

    var body: some View {
        let mode = program.intensityMode
        ScrollView {
            VStack(alignment: .leading, spacing: 0) {
                hero
                ForEach(Array(day.exercises.enumerated()), id: \.element.id) { index, ex in
                    exerciseBlock(ex, index: index, mode: mode)
                }
            }
            .padding(.bottom, 24)
        }
        .background(Color.bg)
        .scrollIndicators(.hidden)
        .navigationTitle("")
        .navigationBarTitleDisplayMode(.inline)
        .safeAreaInset(edge: .bottom) {
            Button { navigate(.activeSession) } label: {
                Label("Start workout", systemImage: "play.fill")
            }
            .buttonStyle(.editorialPrimary)
            .padding(.horizontal, 20)
            .padding(.vertical, 10)
            .background(.thinMaterial)
        }
    }

    private var hero: some View {
        VStack(alignment: .leading, spacing: 0) {
            Text("Day \(dayIndex + 1) · \(program.name) · Week \(program.currentWeek ?? 1)")
                .font(.system(size: 10, weight: .semibold)).tracking(1.2)
                .foregroundStyle(accent)
            Text(day.name)
                .font(.system(size: 30, weight: .medium, design: .serif))
                .foregroundStyle(.ink).padding(.top, 4)
            Text("\(day.exercises.count) exercises · \(day.muscleSummary)")
                .font(.footnote).foregroundStyle(.ink2).padding(.top, 8)
        }
        .padding(.horizontal, 24)
        .padding(.top, 8)
        .padding(.bottom, 20)
        .overlay(alignment: .bottom) { Divider().overlay(Color.hairline) }
    }

    private func exerciseBlock(_ ex: MockData.ProgramExercise, index: Int, mode: MockData.IntensityMode) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            VStack(alignment: .leading, spacing: 2) {
                Text(ex.name).font(.figureSmall).foregroundStyle(.ink)
                Text(ex.muscle).font(.caption).foregroundStyle(.ink2)
            }
            HStack(spacing: 0) {
                schemePair("Sets", "\(ex.sets)")
                Spacer()
                schemePair("Reps", ex.reps)
                if mode != .off {
                    Spacer()
                    schemePair(mode.title, ex.intensityTarget)
                }
                Spacer()
                schemePair("Rest", rests[min(index, rests.count - 1)])
            }
            Text("Progression — \(program.progressionStrategy)")
                .font(.caption).foregroundStyle(.ink3)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(.horizontal, 20)
        .padding(.vertical, 18)
        .overlay(alignment: .bottom) { Divider().overlay(Color.hairline) }
    }

    private func schemePair(_ label: String, _ value: String) -> some View {
        VStack(alignment: .leading, spacing: 2) {
            Text(label)
                .font(.system(size: 9, weight: .semibold))
                .textCase(.uppercase).tracking(1.0)
                .foregroundStyle(.ink3)
            Text(value).font(.system(size: 15, weight: .medium)).monospacedDigit().foregroundStyle(.ink)
        }
    }
}

#Preview {
    NavigationStack {
        ProgramDayView(dayIndex: 0)
            .environment(\.editorialAccent, AccentChoice.clay.color(for: .light))
    }
}
