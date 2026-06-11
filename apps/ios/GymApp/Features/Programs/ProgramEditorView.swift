//
//  ProgramEditorView.swift
//  GymApp
//
//  Program builder (Direction A §5): a horizontal day rail (+ Add day), a
//  full-width "Intensity tracking · Whole program" card with a global
//  RPE/RIR/Off MiniSegmented, then per-exercise blocks — Sets, a Range/Target
//  MiniSegmented + rep value, and (only when intensity isn't Off) an intensity
//  target field whose label derives from the global mode. Editing is local-only.
//

import SwiftUI

struct ProgramEditorView: View {
    @Environment(\.editorialAccent) private var accent
    @Environment(ProgramsStore.self) private var store

    @State private var program: MockData.Program = .init(name: "", goal: "", daysPerWeek: 1, weeks: 8)
    @State private var dayIndex = 0
    @State private var loaded = false

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 0) {
                header
                dayRail
                intensityCard
                exerciseList
            }
            .padding(.bottom, 24)
        }
        .background(Color.bg)
        .scrollIndicators(.hidden)
        .navigationTitle("Edit program")
        .navigationBarTitleDisplayMode(.inline)
        .onAppear {
            guard !loaded else { return }
            program = store.active ?? MockData.blankProgram
            loaded = true
        }
    }

    private var currentDay: MockData.ProgramDay? {
        program.days.indices.contains(dayIndex) ? program.days[dayIndex] : nil
    }

    // MARK: Header (name + meta)

    private var header: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(program.name.isEmpty ? "New program" : program.name)
                .font(.largeTitleSerif).foregroundStyle(.ink)
                .fixedSize(horizontal: false, vertical: true)
            Text("\(program.goal) · \(program.progressionStrategy) · \(program.weeks) weeks")
                .font(.footnote).foregroundStyle(.ink2)
        }
        .padding(.horizontal, 24)
        .padding(.top, 8)
        .padding(.bottom, 18)
    }

    // MARK: Day rail

    private var dayRail: some View {
        ScrollView(.horizontal) {
            HStack(spacing: 8) {
                ForEach(Array(program.days.enumerated()), id: \.element.id) { index, day in
                    Button { dayIndex = index } label: {
                        Text(day.name)
                            .font(.system(size: 12, weight: .semibold))
                            .textCase(.uppercase).tracking(0.8)
                            .foregroundStyle(index == dayIndex ? .bg : .ink2)
                            .padding(.horizontal, 14).padding(.vertical, 7)
                            .background {
                                if index == dayIndex {
                                    Capsule().fill(Color.ink)
                                } else {
                                    Capsule().stroke(Color.hairline, lineWidth: 1)
                                }
                            }
                    }
                    .buttonStyle(.plain)
                }
                Button { addDay() } label: {
                    Text("+ Add day")
                        .font(.system(size: 12, weight: .semibold))
                        .textCase(.uppercase).tracking(0.8)
                        .foregroundStyle(.ink2)
                        .padding(.horizontal, 14).padding(.vertical, 7)
                        .overlay(
                            Capsule().stroke(style: StrokeStyle(lineWidth: 1, dash: [4, 3]))
                                .foregroundStyle(Color.hairline))
                }
                .buttonStyle(.plain)
            }
            .padding(.horizontal, 20)
        }
        .scrollIndicators(.hidden)
        .padding(.bottom, 18)
    }

    // MARK: Global intensity card

    private var intensityCard: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack {
                Text("Intensity tracking").font(.headline).foregroundStyle(.ink)
                Spacer()
                Text("Whole program")
                    .font(.system(size: 10, weight: .semibold))
                    .textCase(.uppercase).tracking(1.0)
                    .foregroundStyle(.ink3)
            }
            MiniSegmented(
                selection: Binding(
                    get: { program.intensityMode },
                    set: { program.intensityMode = $0 }
                ),
                options: MockData.IntensityMode.allCases.map { ($0, $0.title) }
            )
            Text("Applies to every exercise in the program.")
                .font(.caption).foregroundStyle(.ink2)
        }
        .padding(16)
        .overlay(RoundedRectangle(cornerRadius: 6).stroke(Color.hairline, lineWidth: 1))
        .padding(.horizontal, 20)
        .padding(.bottom, 20)
    }

    // MARK: Exercise list

    private var exerciseList: some View {
        VStack(alignment: .leading, spacing: 0) {
            if let day = currentDay {
                Text(day.name).kicker().padding(.horizontal, 20).padding(.bottom, 12)
                ForEach(Array(day.exercises.enumerated()), id: \.element.id) { index, _ in
                    exerciseBlock(dayIndex: dayIndex, exerciseIndex: index)
                }
            }
            Button { addExercise() } label: {
                Text("+ Add exercise")
                    .font(.system(size: 14, weight: .semibold)).foregroundStyle(.ink2)
                    .frame(maxWidth: .infinity).frame(height: 46)
                    .overlay(
                        RoundedRectangle(cornerRadius: 8)
                            .stroke(style: StrokeStyle(lineWidth: 1, dash: [5, 4]))
                            .foregroundStyle(Color.hairline))
            }
            .buttonStyle(.plain)
            .padding(.horizontal, 20)
            .padding(.top, 6)
        }
    }

    private func exerciseBlock(dayIndex di: Int, exerciseIndex ei: Int) -> some View {
        let ex = program.days[di].exercises[ei]
        let mode = program.intensityMode
        return VStack(alignment: .leading, spacing: 14) {
            HStack(spacing: 10) {
                Image(systemName: "line.3.horizontal")
                    .font(.system(size: 14)).foregroundStyle(.ink3)
                VStack(alignment: .leading, spacing: 2) {
                    Text(ex.name).font(.bodyText).foregroundStyle(.ink)
                    Text(ex.muscle).font(.caption).foregroundStyle(.ink2)
                }
                Spacer(minLength: 8)
                Button { removeExercise(di: di, ei: ei) } label: {
                    Image(systemName: "trash")
                        .font(.system(size: 14)).foregroundStyle(.ink3)
                }
                .buttonStyle(.plain)
            }

            HStack(alignment: .bottom, spacing: 18) {
                fieldGroup("Sets") {
                    Stepper(value: setsBinding(di: di, ei: ei), in: 1...8) {
                        Text("\(ex.sets)").font(.system(size: 16, weight: .medium)).monospacedDigit().foregroundStyle(.ink)
                    }
                    .labelsHidden()
                    .fixedSize()
                }
                fieldGroup("Reps") {
                    VStack(alignment: .leading, spacing: 8) {
                        MiniSegmented(
                            selection: repModeBinding(di: di, ei: ei),
                            options: MockData.RepMode.allCases.map { ($0, $0.title) }
                        )
                        .frame(width: 132)
                        Text(ex.reps)
                            .font(.system(size: 16, weight: .medium)).monospacedDigit().foregroundStyle(.ink)
                            .frame(minWidth: 60, alignment: .leading)
                            .padding(.horizontal, 12).padding(.vertical, 6)
                            .overlay(RoundedRectangle(cornerRadius: 6).stroke(Color.hairline, lineWidth: 1))
                    }
                }
                Spacer(minLength: 0)
            }

            if mode != .off {
                fieldGroup(mode.targetLabel) {
                    Text(ex.intensityTarget)
                        .font(.system(size: 16, weight: .medium)).monospacedDigit().foregroundStyle(.ink)
                        .frame(minWidth: 60, alignment: .leading)
                        .padding(.horizontal, 12).padding(.vertical, 6)
                        .overlay(RoundedRectangle(cornerRadius: 6).stroke(Color.hairline, lineWidth: 1))
                }
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(.horizontal, 20)
        .padding(.vertical, 16)
        .overlay(alignment: .top) { Divider().overlay(Color.hairline) }
    }

    private func fieldGroup<Content: View>(_ label: String, @ViewBuilder content: () -> Content) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(label)
                .font(.system(size: 9, weight: .semibold))
                .textCase(.uppercase).tracking(1.0)
                .foregroundStyle(.ink3)
            content()
        }
    }

    // MARK: Bindings into the nested model

    private func setsBinding(di: Int, ei: Int) -> Binding<Int> {
        Binding(
            get: { program.days[di].exercises[ei].sets },
            set: { program.days[di].exercises[ei].sets = $0 }
        )
    }

    private func repModeBinding(di: Int, ei: Int) -> Binding<MockData.RepMode> {
        Binding(
            get: { program.days[di].exercises[ei].repMode },
            set: { newMode in
                var ex = program.days[di].exercises[ei]
                // Switching mode reshapes the rep value display: range ↔ single.
                if newMode == .target, ex.reps.contains("–") {
                    ex.reps = ex.reps.split(separator: "–").last.map(String.init) ?? ex.reps
                } else if newMode == .range, !ex.reps.contains("–") {
                    let n = Int(ex.reps) ?? 8
                    ex.reps = "\(max(1, n - 2))–\(n)"
                }
                ex.repMode = newMode
                program.days[di].exercises[ei] = ex
            }
        )
    }

    // MARK: Mutations

    private func addDay() {
        let n = program.days.count + 1
        program.days.append(.init(name: "Day \(n)", exercises: []))
        dayIndex = program.days.count - 1
    }

    private func addExercise() {
        guard program.days.indices.contains(dayIndex) else { return }
        program.days[dayIndex].exercises.append(
            .init(name: "New exercise", muscle: "—", sets: 3, reps: "8–12", intensityTarget: "8")
        )
    }

    private func removeExercise(di: Int, ei: Int) {
        guard program.days.indices.contains(di),
              program.days[di].exercises.indices.contains(ei) else { return }
        program.days[di].exercises.remove(at: ei)
    }
}

#Preview {
    NavigationStack {
        ProgramEditorView()
            .environment(ProgramsStore())
            .environment(\.editorialAccent, AccentChoice.clay.color(for: .light))
    }
}
