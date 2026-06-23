//
//  ProgramEditorView.swift
//  GymApp
//
//  Program builder (Direction A §6). A draggable slot rail (per-slot Rest toggle,
//  "+ Add slot" → live N-slot microcycle, `.onMove` reorder), a program-level
//  details card (Intensity RPE/RIR/Off, and when periodization is set a Mesocycle
//  length control + Auto-deload toggle), then the selected slot's exercise list —
//  hidden for rest slots. Editing is local-only; no persistence.
//

import SwiftUI

struct ProgramEditorView: View {
    @Environment(\.editorialAccent) private var accent
    @Environment(ProgramsStore.self) private var store

    @State private var program: MockData.Program = .init(name: "", goal: "", microcycleLength: 1)
    @State private var slotIndex = 0
    @State private var loaded = false

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 0) {
                header
                slotRail
                detailsCard
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

    private var currentSlot: MockData.ProgramDay? {
        program.days.indices.contains(slotIndex) ? program.days[slotIndex] : nil
    }

    private var trainingSlotCount: Int { program.days.filter { !$0.isRestDay }.count }
    private var hasPeriodization: Bool {
        // Mesocycle controls surface when a progression strategy is set (mirrors
        // the web's "periodization is set" gate).
        !program.progressionStrategy.isEmpty
    }

    // MARK: Header (name + live microcycle length)

    private var header: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(program.name.isEmpty ? "New program" : program.name)
                .font(.largeTitleSerif).foregroundStyle(.ink)
                .fixedSize(horizontal: false, vertical: true)
            Text("\(program.goal) · \(program.days.count)-slot microcycle · \(trainingSlotCount) training")
                .font(.footnote).foregroundStyle(.ink2)
        }
        .padding(.horizontal, 24)
        .padding(.top, 8)
        .padding(.bottom, 18)
    }

    // MARK: Slot rail (draggable, per-slot rest toggle, + Add slot)

    private var slotRail: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack {
                Text("Slots").kicker()
                Spacer()
                Text("\(program.days.count)-slot microcycle")
                    .font(.system(size: 10, weight: .semibold))
                    .textCase(.uppercase).tracking(1.0)
                    .foregroundStyle(.ink3)
            }
            .padding(.horizontal, 24)

            List {
                ForEach(Array(program.days.enumerated()), id: \.element.id) { index, slot in
                    slotRailRow(slot, index: index)
                        .listRowInsets(EdgeInsets(top: 0, leading: 20, bottom: 0, trailing: 20))
                        .listRowSeparator(.hidden)
                        .listRowBackground(Color.bg)
                }
                .onMove(perform: moveSlots)

                addSlotRow
                    .listRowInsets(EdgeInsets(top: 10, leading: 20, bottom: 0, trailing: 20))
                    .listRowSeparator(.hidden)
                    .listRowBackground(Color.bg)
            }
            .listStyle(.plain)
            .scrollDisabled(true)
            .frame(height: slotRailHeight)
            .environment(\.editMode, .constant(.active))
        }
        .padding(.bottom, 18)
    }

    private var slotRailHeight: CGFloat {
        CGFloat(program.days.count) * 60 + 62
    }

    private func slotRailRow(_ slot: MockData.ProgramDay, index: Int) -> some View {
        VStack(spacing: 0) {
            HStack(spacing: 12) {
                Button { slotIndex = index } label: {
                    VStack(alignment: .leading, spacing: 2) {
                        Text(slot.isRestDay ? "Rest" : slot.name)
                            .font(.system(size: 15, weight: .medium, design: slot.isRestDay ? .serif : .default))
                            .italic(slot.isRestDay)
                            .foregroundStyle(index == slotIndex ? accent : (slot.isRestDay ? .ink3 : .ink))
                        Text(slot.isRestDay ? "Rest slot" : "\(slot.exercises.count) exercises")
                            .font(.caption).foregroundStyle(.ink2)
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .contentShape(Rectangle())
                }
                .buttonStyle(.plain)

                Toggle("Rest", isOn: restBinding(index: index))
                    .labelsHidden()
                    .toggleStyle(.switch)
                    .tint(accent)
                    .fixedSize()

                Button { removeSlot(index: index) } label: {
                    Image(systemName: "trash")
                        .font(.system(size: 14)).foregroundStyle(.ink3)
                }
                .buttonStyle(.plain)
                .disabled(program.days.count <= 1)
            }
            .frame(minHeight: 58)
            Rectangle().fill(Color.hairline).frame(height: 1)
        }
    }

    private var addSlotRow: some View {
        Button { addSlot() } label: {
            Text("+ Add slot")
                .font(.system(size: 14, weight: .semibold)).foregroundStyle(.ink2)
                .frame(maxWidth: .infinity).frame(height: 44)
                .overlay(
                    RoundedRectangle(cornerRadius: 8)
                        .stroke(style: StrokeStyle(lineWidth: 1, dash: [5, 4]))
                        .foregroundStyle(Color.hairline))
        }
        .buttonStyle(.plain)
    }

    // MARK: Program-level details (intensity + mesocycle)

    private var detailsCard: some View {
        VStack(alignment: .leading, spacing: 18) {
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

            if hasPeriodization {
                Divider().overlay(Color.hairline)
                mesocycleControls
            }
        }
        .padding(16)
        .overlay(RoundedRectangle(cornerRadius: 6).stroke(Color.hairline, lineWidth: 1))
        .padding(.horizontal, 20)
        .padding(.bottom, 20)
    }

    private var mesocycleControls: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Mesocycle").font(.headline).foregroundStyle(.ink)
            HStack(alignment: .center, spacing: 14) {
                VStack(alignment: .leading, spacing: 2) {
                    Text("Length")
                        .font(.system(size: 13, weight: .medium)).foregroundStyle(.ink)
                    Text("Microcycles, deload excluded")
                        .font(.caption).foregroundStyle(.ink2)
                }
                Spacer(minLength: 8)
                Stepper(value: Binding(
                    get: { program.mesocycleLengthMicrocycles },
                    set: { program.mesocycleLengthMicrocycles = $0 }
                ), in: 1...12) {
                    Text("\(program.mesocycleLengthMicrocycles)")
                        .font(.system(size: 16, weight: .medium)).monospacedDigit().foregroundStyle(.ink)
                }
                .labelsHidden()
                .fixedSize()
            }
            Toggle(isOn: Binding(
                get: { program.autoDeload },
                set: { program.autoDeload = $0 }
            )) {
                VStack(alignment: .leading, spacing: 2) {
                    Text("Auto-deload")
                        .font(.system(size: 13, weight: .medium)).foregroundStyle(.ink)
                    Text("Append a deload microcycle after the block")
                        .font(.caption).foregroundStyle(.ink2)
                }
            }
            .tint(accent)
        }
    }

    // MARK: Exercise list (hidden for rest slots)

    @ViewBuilder
    private var exerciseList: some View {
        if let slot = currentSlot {
            if slot.isRestDay {
                VStack(alignment: .leading, spacing: 6) {
                    Text(slot.name).kicker()
                    Text("Rest day — no exercises")
                        .font(.system(size: 16, design: .serif)).italic()
                        .foregroundStyle(.ink3)
                }
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding(.horizontal, 20)
                .padding(.vertical, 24)
                .overlay(alignment: .top) { Divider().overlay(Color.hairline) }
            } else {
                VStack(alignment: .leading, spacing: 0) {
                    Text(slot.name).kicker().padding(.horizontal, 20).padding(.bottom, 12)
                    ForEach(Array(slot.exercises.enumerated()), id: \.element.id) { index, _ in
                        exerciseBlock(slotIndex: slotIndex, exerciseIndex: index)
                    }
                    addExerciseRow
                }
            }
        }
    }

    private var addExerciseRow: some View {
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

    private func exerciseBlock(slotIndex di: Int, exerciseIndex ei: Int) -> some View {
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

    private func restBinding(index: Int) -> Binding<Bool> {
        Binding(
            get: { program.days.indices.contains(index) ? program.days[index].isRestDay : false },
            set: { isRest in
                guard program.days.indices.contains(index) else { return }
                program.days[index].isRestDay = isRest
                if isRest {
                    program.days[index].name = "Rest"
                    program.days[index].muscleSummary = ""
                } else if program.days[index].name == "Rest" {
                    program.days[index].name = "Slot \(index + 1)"
                }
            }
        )
    }

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

    private func moveSlots(from source: IndexSet, to destination: Int) {
        program.days.move(fromOffsets: source, toOffset: destination)
        reindexSlots()
        // Keep selection following the dragged row where possible.
        if let first = source.first {
            let newIndex = first < destination ? destination - 1 : destination
            slotIndex = min(max(0, newIndex), program.days.count - 1)
        }
    }

    private func addSlot() {
        let n = program.days.count + 1
        program.days.append(.init(slotIndex: n - 1, name: "Slot \(n)", exercises: []))
        program.microcycleLength = program.days.count
        slotIndex = program.days.count - 1
    }

    private func removeSlot(index: Int) {
        guard program.days.count > 1, program.days.indices.contains(index) else { return }
        program.days.remove(at: index)
        reindexSlots()
        program.microcycleLength = program.days.count
        slotIndex = min(slotIndex, program.days.count - 1)
    }

    /// Rewrites each slot's `slotIndex` to its array position after a move/remove.
    private func reindexSlots() {
        for i in program.days.indices { program.days[i].slotIndex = i }
    }

    private func addExercise() {
        guard program.days.indices.contains(slotIndex), !program.days[slotIndex].isRestDay else { return }
        program.days[slotIndex].exercises.append(
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
