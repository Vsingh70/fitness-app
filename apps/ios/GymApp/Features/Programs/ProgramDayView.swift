//
//  ProgramDayView.swift
//  GymApp
//
//  Per-day detail (Direction A §6 · design IosPerDay / .pix-*): day hero over a
//  2px ink rule, each exercise as an indexed block with a Sets / Reps /
//  {RPE|RIR} / Rest scheme and a "Progression — …" line, plus a Start workout
//  action.
//

import SwiftUI

struct ProgramDayView: View {
    @Environment(\.editorialAccent) private var accent
    @Environment(ProgramsStore.self) private var store
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

    private var totalSets: Int { day.exercises.reduce(0) { $0 + $1.sets } }
    private var estMinutes: Int { Int((Double(totalSets) * 2.5).rounded()) }

    var body: some View {
        let mode = program.intensityMode
        ScrollView {
            VStack(alignment: .leading, spacing: 0) {
                if day.isRestDay {
                    restHero
                        .padding(.horizontal, 22)
                } else {
                    hero
                        .padding(.horizontal, 22)
                    VStack(alignment: .leading, spacing: 0) {
                        ForEach(Array(day.exercises.enumerated()), id: \.element.id) { index, ex in
                            exerciseBlock(ex, index: index, mode: mode)
                        }
                    }
                    .padding(.horizontal, 22)
                }
            }
            .padding(.bottom, 24)
        }
        .background(Color.bg)
        .scrollIndicators(.hidden)
        .navigationTitle("")
        .navigationBarTitleDisplayMode(.inline)
        .safeAreaInset(edge: .bottom) {
            if !day.isRestDay {
                Button { navigate(.activeSession) } label: {
                    Label("Start workout", systemImage: "play.fill").frame(maxWidth: .infinity)
                }
                .buttonStyle(.editorialPrimary)
                .padding(.horizontal, 16)
                .padding(.vertical, 10)
                .background(.thinMaterial)
            }
        }
    }

    // Rest-slot state — no exercises, no Start.
    private var restHero: some View {
        VStack(alignment: .leading, spacing: 0) {
            Text("Slot \(dayIndex + 1) · \(program.goal) · Cycle \(program.currentRepetition)")
                .font(.system(size: 10, weight: .semibold)).textCase(.uppercase)
                .tracking(1.4).foregroundStyle(.ink3)
            Text("Rest day")
                .font(.system(size: 27, weight: .medium, design: .serif)).italic()
                .foregroundStyle(.ink2).padding(.top, 4)
            Text("No exercises scheduled. Recover, eat, and come back for the next training slot.")
                .font(.system(size: 13)).foregroundStyle(.ink2).lineSpacing(2)
                .padding(.top, 8)
                .fixedSize(horizontal: false, vertical: true)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(.bottom, 12)
        .padding(.top, 8)
        .overlay(alignment: .bottom) { Rectangle().fill(Color.ink).frame(height: 2) }
    }

    // pix-hero
    private var hero: some View {
        VStack(alignment: .leading, spacing: 0) {
            Text("Slot \(dayIndex + 1) · \(program.goal) · Cycle \(program.currentRepetition)")
                .font(.system(size: 10, weight: .semibold)).textCase(.uppercase)
                .tracking(1.4).foregroundStyle(accent)
            Text(day.name)
                .font(.system(size: 27, weight: .medium, design: .serif))
                .foregroundStyle(.ink).padding(.top, 4)
            Text("\(day.exercises.count) exercises · \(totalSets) sets · ~\(estMinutes) min")
                .font(.system(size: 12)).foregroundStyle(.ink2).padding(.top, 6)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(.bottom, 12)
        .overlay(alignment: .bottom) { Rectangle().fill(Color.ink).frame(height: 2) }
    }

    // pix-ex
    private func exerciseBlock(
        _ ex: MockData.ProgramExercise, index: Int, mode: MockData.IntensityMode
    ) -> some View {
        VStack(alignment: .leading, spacing: 0) {
            HStack(alignment: .firstTextBaseline, spacing: 10) {
                Text(String(format: "%02d", index + 1))
                    .font(.system(size: 12, design: .serif)).monospacedDigit()
                    .foregroundStyle(.ink3).frame(width: 18, alignment: .leading)
                Text(ex.name)
                    .font(.system(size: 17, weight: .medium, design: .serif)).foregroundStyle(.ink)
            }
            HStack(spacing: 18) {
                schemeCell("\(ex.sets)", "Sets")
                schemeCell(ex.reps, "Reps")
                if mode != .off {
                    schemeCell(ex.intensityTarget, mode.title)
                }
                schemeCell(rests[min(index, rests.count - 1)], "Rest")
            }
            .padding(.top, 8).padding(.leading, 28)
            (Text("Progression — ")
                .foregroundStyle(.ink2)
                + Text(program.progressionStrategy)
                .foregroundStyle(accent))
                .font(.system(size: 11))
                .padding(.top, 8).padding(.leading, 28)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(.vertical, 14)
        .overlay(alignment: .bottom) { Rectangle().fill(Color.hairline).frame(height: 1) }
    }

    private func schemeCell(_ value: String, _ label: String) -> some View {
        VStack(alignment: .leading, spacing: 2) {
            Text(value)
                .font(.system(size: 15, weight: .medium, design: .serif))
                .monospacedDigit().foregroundStyle(.ink)
            Text(label)
                .font(.system(size: 9, weight: .semibold)).textCase(.uppercase)
                .tracking(0.8).foregroundStyle(.ink3)
        }
    }
}

#Preview {
    NavigationStack {
        ProgramDayView(dayIndex: 0)
            .environment(ProgramsStore())
            .environment(\.editorialAccent, AccentChoice.clay.color(for: .light))
    }
}
