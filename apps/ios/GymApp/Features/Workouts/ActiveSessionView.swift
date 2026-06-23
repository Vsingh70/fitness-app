//
//  ActiveSessionView.swift
//  GymApp
//
//  Workout-in-progress: exercise pill rail, active exercise card with plate
//  math + set rows, inline set entry, floating rest bar, finish/skip. Mirrors
//  ScreenActiveIOS, now driven live by `WorkoutsStore` (log → rest → finish).
//

import SwiftUI

struct ActiveSessionView: View {
    @Environment(\.editorialAccent) private var accent
    @Environment(\.dismiss) private var dismiss
    @Environment(WorkoutsStore.self) private var store

    /// Inline new-set entry.
    @State private var weightText = ""
    @State private var repsText = ""
    @State private var rpeText = ""
    @State private var isLogging = false

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 0) {
                if let active = store.active {
                    titleBlock(active)
                    exerciseRail(active)
                    activeCard(active)
                } else {
                    emptyState
                }
            }
            .padding(.bottom, 120)
        }
        .background(Color.bg)
        .scrollIndicators(.hidden)
        .safeAreaInset(edge: .bottom) {
            if store.isResting {
                RestBar(
                    elapsed: store.restElapsedLabel,
                    total: store.restTotalLabel,
                    fraction: store.restFraction,
                    onAddTime: { store.addRestTime(30) },
                    onSkip: { store.stopRest() }
                )
                .padding(.horizontal, 16)
                .padding(.bottom, 8)
            }
        }
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .topBarLeading) {
                Button { dismiss() } label: {
                    Label("Back", systemImage: "chevron.left")
                }
            }
            ToolbarItem(placement: .principal) {
                Text(store.active?.kicker ?? "Workout")
                    .font(.system(size: 16, weight: .semibold, design: .serif))
                    .foregroundStyle(.ink)
            }
            ToolbarItem(placement: .topBarTrailing) {
                Menu {
                    Button("Finish", role: .none) { finish() }
                    Button("Skip session", role: .destructive) { skip() }
                } label: {
                    Text("Finish").fontWeight(.semibold).foregroundStyle(.destructive)
                }
                .disabled(store.isMutating)
            }
        }
        .alert(
            "Couldn’t complete that",
            isPresented: Binding(
                get: { store.actionError != nil },
                set: { if !$0 { store.actionError = nil } }
            )
        ) {
            Button("OK", role: .cancel) { store.actionError = nil }
        } message: {
            Text(store.actionError ?? "")
        }
    }

    // MARK: Empty

    private var emptyState: some View {
        VStack(spacing: 12) {
            Text("No active session")
                .font(.titleSerif).foregroundStyle(.ink)
            Text("Start a workout from the Workouts tab.")
                .font(.footnote).foregroundStyle(.ink2)
        }
        .frame(maxWidth: .infinity)
        .padding(.top, 80)
    }

    // MARK: Title block

    private func titleBlock(_ active: WorkoutsStore.ActiveView) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(active.kicker)
                .font(.system(size: 12, weight: .semibold))
                .textCase(.uppercase)
                .tracking(0.7)
                .foregroundStyle(accent)
            Text(active.position).font(.titleSerif).foregroundStyle(.ink)
            Text(active.setsComplete).font(.footnote).foregroundStyle(.ink2)
        }
        .padding(.horizontal, 20)
        .padding(.bottom, 12)
    }

    // MARK: Exercise rail

    private func exerciseRail(_ active: WorkoutsStore.ActiveView) -> some View {
        ScrollView(.horizontal) {
            HStack(spacing: 6) {
                ForEach(Array(active.rail.enumerated()), id: \.element.id) { idx, ex in
                    Button {
                        store.focusedExerciseIndex = idx
                        store.refocus()
                    } label: {
                        exercisePill(ex)
                    }
                    .buttonStyle(.plain)
                }
            }
            .padding(.horizontal, 20)
        }
        .scrollIndicators(.hidden)
        .padding(.bottom, 16)
    }

    private func exercisePill(_ ex: WorkoutsStore.RailItem) -> some View {
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

    private func activeCard(_ active: WorkoutsStore.ActiveView) -> some View {
        VStack(alignment: .leading, spacing: 0) {
            HStack(alignment: .top) {
                VStack(alignment: .leading, spacing: 2) {
                    Text(active.activeExerciseName).font(.titleSerif).foregroundStyle(.ink)
                    Text("\(active.sets.count) set\(active.sets.count == 1 ? "" : "s") logged")
                        .font(.caption).foregroundStyle(.ink2)
                }
                Spacer()
            }
            .padding(.bottom, 4)

            VStack(spacing: 4) {
                ForEach(active.sets) { set in
                    setRow(set)
                }
            }
            .padding(.top, 8)

            newSetRow(active)
                .padding(.top, 8)
        }
        .padding(16)
        .overlay(
            RoundedRectangle(cornerRadius: 4).stroke(Color.hairline, lineWidth: 1)
        )
        .padding(.horizontal, 20)
    }

    // MARK: Logged set row

    private func setRow(_ set: WorkoutsStore.LiveSet) -> some View {
        HStack(spacing: 8) {
            Text("\(set.index)")
                .font(.system(size: 15, weight: .bold, design: .serif))
                .monospacedDigit()
                .foregroundStyle(.ink2)
                .frame(width: 28)
            Text(set.weight.isEmpty ? "–" : set.weight)
                .font(.system(size: 17, weight: .semibold))
                .monospacedDigit()
                .foregroundStyle(.success)
                .frame(maxWidth: .infinity)
            Text(set.reps.isEmpty ? "–" : set.reps)
                .font(.system(size: 17, weight: .semibold))
                .monospacedDigit()
                .foregroundStyle(.success)
                .frame(maxWidth: .infinity)
            Text(set.rpe.isEmpty ? "–" : set.rpe)
                .font(.system(size: 13, weight: .semibold))
                .monospacedDigit()
                .foregroundStyle(.ink2)
                .frame(width: 50)
            if set.isPR {
                EditorialChip(text: "PR", tone: .warning, systemImage: "star.fill")
            }
            Button(role: .destructive) {
                Task { await store.deleteSet(setID: set.setID) }
            } label: {
                Image(systemName: "xmark")
                    .font(.system(size: 11, weight: .bold))
                    .foregroundStyle(.ink3)
                    .frame(width: 26, height: 26)
            }
            .buttonStyle(.plain)
        }
        .padding(.horizontal, 8)
        .padding(.vertical, 8)
        .background(RoundedRectangle(cornerRadius: 8).fill(Color.fill))
    }

    // MARK: New set entry

    private func newSetRow(_ active: WorkoutsStore.ActiveView) -> some View {
        VStack(spacing: 8) {
            HStack(spacing: 8) {
                field("Weight", text: $weightText, keyboard: .decimalPad)
                field("Reps", text: $repsText, keyboard: .numberPad)
                field("RPE", text: $rpeText, keyboard: .decimalPad)
            }
            Button {
                logSet()
            } label: {
                Text(isLogging ? "Logging…" : "Log set")
                    .font(.system(size: 14, weight: .semibold))
                    .frame(maxWidth: .infinity)
            }
            .buttonStyle(.editorialPrimary)
            .disabled(isLogging || active.activeExerciseID == nil)
        }
    }

    private func field(_ placeholder: String, text: Binding<String>, keyboard: UIKeyboardType) -> some View {
        TextField(placeholder, text: text)
            .keyboardType(keyboard)
            .multilineTextAlignment(.center)
            .font(.system(size: 17, weight: .semibold))
            .monospacedDigit()
            .foregroundStyle(.ink)
            .frame(height: 40)
            .frame(maxWidth: .infinity)
            .background(RoundedRectangle(cornerRadius: 8).fill(Color.fill))
            .overlay(RoundedRectangle(cornerRadius: 8).stroke(Color.hairline, lineWidth: 1))
    }

    // MARK: Actions

    private func logSet() {
        guard !isLogging else { return }
        let weight = Double(weightText.replacingOccurrences(of: ",", with: "."))
        let reps = Int(repsText)
        let rpe = Double(rpeText.replacingOccurrences(of: ",", with: "."))
        guard weight != nil || reps != nil else { return }
        isLogging = true
        Task {
            await store.logSet(weightKg: weight, reps: reps, rpe: rpe)
            weightText = ""; repsText = ""; rpeText = ""
            isLogging = false
        }
    }

    private func finish() {
        Task {
            await store.finish()
            dismiss()
        }
    }

    private func skip() {
        Task {
            await store.skip()
            dismiss()
        }
    }
}

#Preview {
    NavigationStack {
        ActiveSessionView()
            .environment(WorkoutsStore(preview: true))
            .environment(\.editorialAccent, AccentChoice.clay.color(for: .light))
    }
}
