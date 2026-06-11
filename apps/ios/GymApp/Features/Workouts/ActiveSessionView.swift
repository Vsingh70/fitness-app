//
//  ActiveSessionView.swift
//  GymApp
//
//  Workout-in-progress: exercise pill rail, active exercise card with plate
//  math + set rows, floating rest bar. Mirrors ScreenActiveIOS. Visual only —
//  set logging / rest countdown behavior is out of scope for this pass.
//

import SwiftUI

struct ActiveSessionView: View {
    @Environment(\.editorialAccent) private var accent
    @Environment(\.dismiss) private var dismiss

    private let session = MockData.activeSession

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 0) {
                titleBlock
                exerciseRail
                activeCard
            }
            .padding(.bottom, 120)
        }
        .background(Color.bg)
        .scrollIndicators(.hidden)
        .safeAreaInset(edge: .bottom) {
            RestBar(
                elapsed: session.restElapsed,
                total: session.restTotal,
                fraction: session.restFraction
            )
            .padding(.horizontal, 16)
            .padding(.bottom, 8)
        }
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .topBarLeading) {
                Button { dismiss() } label: {
                    Label("Pause", systemImage: "chevron.left")
                }
            }
            ToolbarItem(placement: .principal) {
                Text(session.elapsed)
                    .font(.system(size: 17, weight: .bold, design: .serif))
                    .monospacedDigit()
                    .foregroundStyle(.ink)
            }
            ToolbarItem(placement: .topBarTrailing) {
                Button("Finish") { dismiss() }
                    .foregroundStyle(.destructive)
                    .fontWeight(.semibold)
            }
        }
    }

    // MARK: Title block

    private var titleBlock: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(session.kicker)
                .font(.system(size: 12, weight: .semibold))
                .textCase(.uppercase)
                .tracking(0.7)
                .foregroundStyle(accent)
            Text(session.position).font(.titleSerif).foregroundStyle(.ink)
            Text(session.setsComplete).font(.footnote).foregroundStyle(.ink2)
        }
        .padding(.horizontal, 20)
        .padding(.bottom, 12)
    }

    // MARK: Exercise rail

    private var exerciseRail: some View {
        ScrollView(.horizontal) {
            HStack(spacing: 6) {
                ForEach(session.exercises) { ex in
                    exercisePill(ex)
                }
            }
            .padding(.horizontal, 20)
        }
        .scrollIndicators(.hidden)
        .padding(.bottom, 16)
    }

    private func exercisePill(_ ex: MockData.ActiveExercise) -> some View {
        let done = ex.doneSets == ex.totalSets && ex.totalSets > 0
        let fg: Color = ex.active ? .bg : (done ? accent : .ink2)
        return Text("\(ex.shortName) · \(ex.doneSets)/\(ex.totalSets)")
            .font(.system(size: 11, weight: .semibold))
            .textCase(.uppercase)
            .tracking(0.5)
            .foregroundStyle(fg)
            .padding(.horizontal, 12)
            .padding(.vertical, 6)
            .background {
                if ex.active {
                    Capsule().fill(Color.ink)
                } else {
                    Capsule().stroke(Color.hairline, lineWidth: 1)
                }
            }
    }

    // MARK: Active exercise card

    private var activeCard: some View {
        VStack(alignment: .leading, spacing: 0) {
            HStack(alignment: .top) {
                VStack(alignment: .leading, spacing: 2) {
                    Text(session.activeExerciseName).font(.titleSerif).foregroundStyle(.ink)
                    Text(session.activeExerciseTarget).font(.caption).foregroundStyle(.ink2)
                }
                Spacer()
                Image(systemName: "arrow.down.left.and.arrow.up.right")
                    .font(.system(size: 18))
                    .foregroundStyle(accent)
            }
            .padding(.bottom, 4)

            PlateMath(plates: session.plates, caption: session.activeWeight)
                .padding(.top, 6)

            VStack(spacing: 4) {
                ForEach(session.sets) { set in
                    setRow(set)
                }
            }
            .padding(.top, 8)

            Button { } label: {
                Text("+ Add set")
                    .font(.system(size: 14))
                    .foregroundStyle(.ink2)
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 10)
                    .overlay(
                        RoundedRectangle(cornerRadius: 10)
                            .stroke(style: StrokeStyle(lineWidth: 1, dash: [4]))
                            .foregroundStyle(.ink3)
                    )
            }
            .buttonStyle(.plain)
            .padding(.top, 8)
        }
        .padding(16)
        .overlay(
            RoundedRectangle(cornerRadius: 4).stroke(Color.hairline, lineWidth: 1)
        )
        .padding(.horizontal, 20)
    }

    // MARK: Set row

    private func setRow(_ set: MockData.WorkoutSet) -> some View {
        HStack(spacing: 8) {
            Text("\(set.index)")
                .font(.system(size: 15, weight: .bold, design: .serif))
                .monospacedDigit()
                .foregroundStyle(.ink2)
                .frame(width: 28)
            Text(set.previous)
                .font(.caption)
                .monospacedDigit()
                .foregroundStyle(.ink3)
                .frame(width: 80, alignment: .leading)
            valueCell(set.weight, set: set)
            valueCell(set.reps.isEmpty ? "–" : set.reps, set: set)
            Text(set.rpe.isEmpty ? "–" : set.rpe)
                .font(.system(size: 13, weight: .semibold))
                .monospacedDigit()
                .foregroundStyle(set.done ? .ink2 : .ink3)
                .frame(width: 50)
            checkmark(set)
        }
        .padding(.horizontal, set.done || set.current ? 8 : 0)
        .padding(.vertical, 8)
        .background(
            RoundedRectangle(cornerRadius: 8)
                .fill(set.done ? Color.fill : (set.current ? accent.opacity(0.10) : .clear))
        )
    }

    private func valueCell(_ text: String, set: MockData.WorkoutSet) -> some View {
        Text(text)
            .font(.system(size: 17, weight: .semibold))
            .monospacedDigit()
            .foregroundStyle(set.done ? .success : .ink)
            .frame(maxWidth: .infinity)
            .frame(height: 36)
            .background {
                if !set.done {
                    RoundedRectangle(cornerRadius: 8).fill(Color.fill)
                }
            }
            .overlay {
                if set.current {
                    RoundedRectangle(cornerRadius: 8).stroke(accent, lineWidth: 1.5)
                } else if !set.done {
                    RoundedRectangle(cornerRadius: 8).stroke(Color.hairline, lineWidth: 1)
                }
            }
    }

    private func checkmark(_ set: MockData.WorkoutSet) -> some View {
        ZStack {
            Circle()
                .fill(set.done ? Color.success : .clear)
                .overlay(Circle().stroke(set.done ? .clear : Color.ink3, lineWidth: 1.5))
            if set.done {
                Image(systemName: "checkmark")
                    .font(.system(size: 12, weight: .bold))
                    .foregroundStyle(.white)
            }
        }
        .frame(width: 26, height: 26)
    }
}

#Preview {
    NavigationStack {
        ActiveSessionView()
            .environment(\.editorialAccent, AccentChoice.clay.color(for: .light))
    }
}
