//
//  ProgramsHomeView.swift
//  GymApp
//
//  The active-program "spine" (Direction A §3). Top to bottom: masthead +
//  mesocycle (cycle) bar, today's slot (rest slot → quiet Rest day + next
//  training slot), the current microcycle as a slot list (rest slots italic /
//  muted), then a My programs library with Activate / Deactivate and an overflow
//  (Duplicate, Save as template). "Create a new program" routes to the chooser —
//  so a template is always an option, not just a blank build.
//

import SwiftUI

struct ProgramsHomeView: View {
    @Environment(ProgramsStore.self) private var store
    @Environment(\.editorialAccent) private var accent
    @Environment(\.programNavigate) private var navigate

    /// The program targeted by the Save-as-template sheet.
    @State private var savingTemplateFor: MockData.Program?

    private var programs: [MockData.Program] { store.programs }
    private var activeProgram: MockData.Program? { store.active }

    var body: some View {
        spine
            .background(Color.bg)
            .navigationTitle("")
            .navigationBarTitleDisplayMode(.inline)
            .sheet(item: $savingTemplateFor) { program in
                SaveAsTemplateSheet(program: program) { name, visibility in
                    store.saveAsTemplate(program, name: name, visibility: visibility)
                }
            }
    }

    // MARK: Routing (host NavigationStack owns the path; we use the shared enum)

    private func routeToChooser() { navigate(.programChooser) }
    private func routeToBuilder() { navigate(.programEditor) }

    // MARK: Spine

    private var spine: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 0) {
                if let active = activeProgram {
                    masthead(active)
                    todayCard(active)
                    thisMicrocycle(active)
                }
                library
            }
            .padding(.bottom, 28)
        }
        .scrollIndicators(.hidden)
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Button("Edit") { routeToBuilder() }
                    .fontWeight(.semibold)
                    .foregroundStyle(accent)
            }
        }
    }

    // MARK: 1 · Masthead + cycle bar

    private func masthead(_ p: MockData.Program) -> some View {
        VStack(alignment: .leading, spacing: 16) {
            HStack(alignment: .top, spacing: 16) {
                VStack(alignment: .leading, spacing: 8) {
                    Text("Active program").kicker()
                    Text(p.name)
                        .font(.largeTitleSerif)
                        .foregroundStyle(.ink)
                        .fixedSize(horizontal: false, vertical: true)
                }
                Spacer(minLength: 8)
                VStack(alignment: .trailing, spacing: 8) {
                    metaPair("Goal", p.goal)
                    metaPair("Intensity", p.intensityMode.title)
                    metaPair("Cycle", microcycleMeta(p))
                }
            }
            MesocycleBarView(
                repetitions: p.mesocycleLengthMicrocycles,
                current: p.currentRepetition,
                autoDeload: p.autoDeload,
                inDeload: p.inDeload
            )
        }
        .padding(.horizontal, 24)
        .padding(.top, 14)
        .padding(.bottom, 24)
    }

    private func metaPair(_ label: String, _ value: String) -> some View {
        VStack(alignment: .trailing, spacing: 1) {
            Text(label)
                .font(.system(size: 9, weight: .semibold))
                .textCase(.uppercase).tracking(1.0)
                .foregroundStyle(.ink3)
            Text(value)
                .font(.system(size: 13, weight: .medium))
                .foregroundStyle(.ink)
                .multilineTextAlignment(.trailing)
        }
    }

    // MARK: 2 · Today card (current rotation slot)

    @ViewBuilder
    private func todayCard(_ p: MockData.Program) -> some View {
        let slot = currentSlot(p)
        VStack(alignment: .leading, spacing: 0) {
            HairlineCard {
                if slot.isRestDay {
                    restToday(p, slot: slot)
                } else {
                    trainingToday(p, slot: slot)
                }
            }
        }
        .padding(.horizontal, 20)
        .padding(.bottom, 24)
    }

    private func trainingToday(_ p: MockData.Program, slot: MockData.ProgramDay) -> some View {
        VStack(alignment: .leading, spacing: 0) {
            Text("Today · current slot")
                .font(.system(size: 11, weight: .semibold))
                .textCase(.uppercase).tracking(1.2)
                .foregroundStyle(accent)
            Text(slot.name).font(.titleSerif).foregroundStyle(.ink).padding(.top, 4)
            Text("\(slot.exercises.count) exercises · \(slot.muscleSummary)")
                .font(.footnote).foregroundStyle(.ink2).padding(.top, 4)
            Button { navigate(.programDay(dayIndex: p.currentSlotIndex)) } label: {
                Label("Start workout", systemImage: "play.fill")
            }
            .buttonStyle(.editorialPrimary)
            .padding(.top, 14)
        }
    }

    private func restToday(_ p: MockData.Program, slot: MockData.ProgramDay) -> some View {
        let next = nextTrainingSlot(p)
        return VStack(alignment: .leading, spacing: 0) {
            Text("Today · current slot")
                .font(.system(size: 11, weight: .semibold))
                .textCase(.uppercase).tracking(1.2)
                .foregroundStyle(.ink3)
            Text("Rest day")
                .font(.titleSerif).italic().foregroundStyle(.ink2).padding(.top, 4)
            if let next {
                Text("Recover today. Next up: \(next.name) · \(next.muscleSummary)")
                    .font(.footnote).foregroundStyle(.ink2).padding(.top, 4)
                    .fixedSize(horizontal: false, vertical: true)
                Button { navigate(.programDay(dayIndex: next.slotIndex)) } label: {
                    Label("Preview next slot", systemImage: "arrow.right")
                }
                .buttonStyle(.editorialSecondary)
                .padding(.top, 14)
            } else {
                Text("Recover today.")
                    .font(.footnote).foregroundStyle(.ink2).padding(.top, 4)
            }
        }
    }

    // MARK: 3 · This microcycle (the program's actual slots)

    private func thisMicrocycle(_ p: MockData.Program) -> some View {
        VStack(alignment: .leading, spacing: 14) {
            SectionHeaderLarge(title: "This microcycle", trailing: "Full calendar")
            VStack(spacing: 0) {
                Rectangle().fill(Color.hairline).frame(height: 1)
                ForEach(Array(p.days.enumerated()), id: \.element.id) { index, slot in
                    slotRow(slot, program: p, index: index)
                }
            }
        }
        .padding(.horizontal, 20)
        .padding(.bottom, 28)
    }

    @ViewBuilder
    private func slotRow(_ slot: MockData.ProgramDay, program p: MockData.Program, index: Int) -> some View {
        let status = slotStatus(slot, program: p)
        VStack(spacing: 0) {
            Button {
                if !slot.isRestDay { navigate(.programDay(dayIndex: index)) }
            } label: {
                HStack(alignment: .center, spacing: 14) {
                    Text("Slot \(index + 1)")
                        .font(.system(size: 11, weight: .semibold))
                        .textCase(.uppercase).tracking(1.0)
                        .foregroundStyle(.ink3)
                        .frame(width: 50, alignment: .leading)
                    if slot.isRestDay {
                        Text("Rest day")
                            .font(.system(size: 16, design: .serif))
                            .italic()
                            .foregroundStyle(.ink3)
                        Spacer(minLength: 8)
                    } else {
                        VStack(alignment: .leading, spacing: 2) {
                            Text(slot.name)
                                .font(.figureSmall)
                                .foregroundStyle(status == .done ? .ink3 : .ink)
                            Text(slot.muscleSummary)
                                .font(.caption).foregroundStyle(.ink2)
                        }
                        Spacer(minLength: 8)
                        Text("\(slot.exercises.count) ex")
                            .font(.caption).monospacedDigit().foregroundStyle(.ink3)
                        statusLabel(status)
                    }
                }
                .frame(minHeight: 56)
                .padding(.vertical, 6)
                .contentShape(Rectangle())
            }
            .buttonStyle(.plain)
            .disabled(slot.isRestDay)
            Rectangle().fill(Color.hairline).frame(height: 1)
        }
    }

    private enum SlotStatus { case done, today, planned }

    private func slotStatus(_ slot: MockData.ProgramDay, program p: MockData.Program) -> SlotStatus {
        if slot.slotIndex == p.currentSlotIndex { return .today }
        if slot.slotIndex < p.currentSlotIndex { return .done }
        return .planned
    }

    @ViewBuilder
    private func statusLabel(_ status: SlotStatus) -> some View {
        switch status {
        case .done:
            statusText("Done", color: .ink3)
        case .today:
            statusText("Today", color: accent)
        case .planned:
            statusText("Planned", color: .ink2)
        }
    }

    private func statusText(_ text: String, color: Color) -> some View {
        Text(text)
            .font(.system(size: 11, weight: .semibold))
            .textCase(.uppercase).tracking(1.0)
            .foregroundStyle(color)
    }

    // MARK: 4 · My programs library

    private var library: some View {
        VStack(alignment: .leading, spacing: 14) {
            HStack(alignment: .lastTextBaseline) {
                Text("My programs").font(.titleSerif).foregroundStyle(.ink)
                Spacer()
                Button { routeToChooser() } label: {
                    Text("+ New program")
                        .font(.system(size: 11, weight: .semibold))
                        .textCase(.uppercase).tracking(1.2)
                        .foregroundStyle(.ink2)
                }
                .buttonStyle(.plain)
            }
            .padding(.bottom, 12)
            .overlay(alignment: .bottom) { Divider().overlay(Color.hairline) }

            VStack(spacing: 0) {
                ForEach(programs) { program in
                    programRow(program)
                }
                createRow
                    .padding(.top, 14)
            }
        }
        .padding(.horizontal, 20)
    }

    private func programRow(_ program: MockData.Program) -> some View {
        VStack(spacing: 0) {
            HStack(spacing: 12) {
                VStack(alignment: .leading, spacing: 3) {
                    Text(program.name)
                        .font(.figureSmall)
                        .foregroundStyle(program.active ? accent : .ink)
                    Text(programSubtitle(program))
                        .font(.caption).foregroundStyle(.ink2)
                }
                Spacer(minLength: 8)
                if program.active {
                    Text("Active")
                        .font(.system(size: 11, weight: .semibold))
                        .textCase(.uppercase).tracking(1.0)
                        .foregroundStyle(accent)
                } else {
                    Button("Activate") { store.activate(program) }
                        .font(.system(size: 11, weight: .semibold))
                        .textCase(.uppercase).tracking(1.0)
                        .foregroundStyle(.ink2)
                        .buttonStyle(.plain)
                }
                rowMenu(program)
            }
            .frame(minHeight: 56)
            Rectangle().fill(Color.hairline).frame(height: 1)
        }
    }

    /// Overflow menu: Activate/Deactivate on touch, Duplicate, Save as template,
    /// Delete. Mirrors the web row overflow.
    private func rowMenu(_ program: MockData.Program) -> some View {
        Menu {
            if program.active {
                Button(role: .destructive) { store.deactivate(program) } label: {
                    Label("Deactivate", systemImage: "pause.circle")
                }
            } else {
                Button { store.activate(program) } label: {
                    Label("Activate", systemImage: "checkmark.circle")
                }
            }
            Button { store.duplicate(program) } label: {
                Label("Duplicate", systemImage: "doc.on.doc")
            }
            Button { savingTemplateFor = program } label: {
                Label("Save as template", systemImage: "square.and.arrow.down")
            }
            Divider()
            Button(role: .destructive) { store.delete(program) } label: {
                Label("Delete", systemImage: "trash")
            }
        } label: {
            Image(systemName: "ellipsis")
                .font(.system(size: 15, weight: .semibold))
                .foregroundStyle(.ink3)
                .frame(width: 30, height: 30)
                .contentShape(Rectangle())
        }
    }

    private var createRow: some View {
        Button { routeToChooser() } label: {
            Text("+ Create a new program")
                .font(.system(size: 14, weight: .semibold))
                .foregroundStyle(.ink2)
                .frame(maxWidth: .infinity)
                .frame(height: 46)
                .overlay(
                    RoundedRectangle(cornerRadius: 8)
                        .stroke(style: StrokeStyle(lineWidth: 1, dash: [5, 4]))
                        .foregroundStyle(Color.hairline)
                )
        }
        .buttonStyle(.plain)
    }

    // MARK: Derived helpers

    private func currentSlot(_ p: MockData.Program) -> MockData.ProgramDay {
        if p.days.indices.contains(p.currentSlotIndex) {
            return p.days[p.currentSlotIndex]
        }
        return p.days.first ?? MockData.pplDays[0]
    }

    /// The next training (non-rest) slot after the current position, wrapping the
    /// microcycle. Nil only if the program is all rest slots.
    private func nextTrainingSlot(_ p: MockData.Program) -> MockData.ProgramDay? {
        let count = p.days.count
        guard count > 0 else { return nil }
        for offset in 1...count {
            let idx = (p.currentSlotIndex + offset) % count
            let slot = p.days[idx]
            if !slot.isRestDay { return slot }
        }
        return nil
    }

    /// "8-slot cycle, N training" — microcycle length + training-slot count.
    private func microcycleMeta(_ p: MockData.Program) -> String {
        let training = p.days.filter { !$0.isRestDay }.count
        return "\(p.microcycleLength)-slot · \(training) training"
    }

    private func programSubtitle(_ p: MockData.Program) -> String {
        if p.active {
            return "Cycle \(p.currentRepetition) of \(p.mesocycleLengthMicrocycles) · \(p.goal.lowercased())"
        }
        return "\(p.microcycleLength)-slot cycle · \(p.goal.lowercased())"
    }
}

// MARK: Save as template sheet

/// Small dialog: a name field + a Private/Shared visibility choice, then saves the
/// program as a new template (mirrors the web "Save as template" dialog).
private struct SaveAsTemplateSheet: View {
    @Environment(\.dismiss) private var dismiss
    @Environment(\.editorialAccent) private var accent

    let program: MockData.Program
    let onSave: (String, MockData.TemplateVisibility) -> Void

    @State private var name: String
    @State private var visibility: MockData.TemplateVisibility = .private

    init(program: MockData.Program, onSave: @escaping (String, MockData.TemplateVisibility) -> Void) {
        self.program = program
        self.onSave = onSave
        _name = State(initialValue: program.name)
    }

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 22) {
                    VStack(alignment: .leading, spacing: 8) {
                        Text("Template name").kicker()
                        TextField("Template name", text: $name)
                            .font(.bodyText)
                            .padding(.horizontal, 14).padding(.vertical, 12)
                            .overlay(RoundedRectangle(cornerRadius: 6).stroke(Color.hairline, lineWidth: 1))
                    }
                    VStack(alignment: .leading, spacing: 8) {
                        Text("Visibility").kicker()
                        MiniSegmented(
                            selection: $visibility,
                            options: [
                                (.private, "Private to me"),
                                (.shared, "Shared with partners"),
                            ]
                        )
                    }
                    Text("Saves a copy of “\(program.name)” to Browse templates. The program itself is unchanged.")
                        .font(.footnote).foregroundStyle(.ink2)
                        .fixedSize(horizontal: false, vertical: true)
                }
                .padding(24)
            }
            .background(Color.bg)
            .navigationTitle("Save as template")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Save") {
                        onSave(name, visibility)
                        dismiss()
                    }
                    .fontWeight(.semibold)
                    .foregroundStyle(accent)
                }
            }
        }
    }
}

// MARK: Navigation bridge

/// Programs-specific routes that the host NavigationStack drives. Passed down via
/// the environment so the onboarding/spine can push without owning a path.
extension EnvironmentValues {
    @Entry var programNavigate: (WorkoutsView.Route) -> Void = { _ in }
    /// Pops the stack back to the active-program overview (used after adopting a
    /// template or building a program).
    @Entry var programPopToOverview: () -> Void = {}
}

#Preview("Spine") {
    NavigationStack {
        ProgramsHomeView()
            .environment(ProgramsStore())
            .environment(\.editorialAccent, AccentChoice.clay.color(for: .light))
    }
}
