//
//  ProgramsStore.swift
//  GymApp
//
//  Shared in-memory library of the user's programs + saved templates for the
//  visual prototype. Activate / deactivate / delete / duplicate / save-as-template
//  / adopt mutate it; the spine, builder, browse and template flow all read the
//  same instance. No persistence, no networking.
//

import SwiftUI

@MainActor
@Observable
final class ProgramsStore {
    var programs: [MockData.Program]
    /// The template gallery — seeds from MockData; user "save as template" appends.
    var templates: [MockData.ProgramTemplate]

    init(
        programs: [MockData.Program] = MockData.myPrograms,
        templates: [MockData.ProgramTemplate] = MockData.templates
    ) {
        self.programs = programs
        self.templates = templates
    }

    var active: MockData.Program? { programs.first { $0.active } }

    // MARK: Activation

    func activate(_ program: MockData.Program) {
        for i in programs.indices { programs[i].active = false }
        if let i = programs.firstIndex(where: { $0.id == program.id }) {
            programs[i].active = true
        }
    }

    /// Deactivates without deleting — the program keeps its position (bug 5).
    func deactivate(_ program: MockData.Program) {
        if let i = programs.firstIndex(where: { $0.id == program.id }) {
            programs[i].active = false
        }
    }

    func delete(_ program: MockData.Program) {
        programs.removeAll { $0.id == program.id }
    }

    // MARK: Create / duplicate / adopt

    /// Copies a template into a new program (mirrors "Use this template"). The new
    /// program lands inactive — the user activates it from the spine when ready.
    func adopt(_ template: MockData.ProgramTemplate) {
        let new = MockData.Program(
            name: template.name,
            goal: template.goal,
            intensityMode: .rpe,
            microcycleLength: template.microcycleLength,
            mesocycleLengthMicrocycles: template.mesocycleLengthMicrocycles,
            currentSlotIndex: 0,
            currentRepetition: 1,
            inDeload: false,
            active: false,
            days: template.days
        )
        programs.append(new)
    }

    /// Forks a program into a new editable, inactive copy named "... (copy)".
    @discardableResult
    func duplicate(_ program: MockData.Program) -> MockData.Program {
        var copy = program
        // `id` is `let` with a default UUID(); a value-type copy keeps the source
        // id, so re-create via the memberwise init to get a fresh identity.
        copy = MockData.Program(
            name: "\(program.name) (copy)",
            goal: program.goal,
            progressionStrategy: program.progressionStrategy,
            intensityMode: program.intensityMode,
            microcycleLength: program.microcycleLength,
            mesocycleLengthMicrocycles: program.mesocycleLengthMicrocycles,
            autoDeload: program.autoDeload,
            currentSlotIndex: 0,
            currentRepetition: 1,
            inDeload: false,
            active: false,
            days: program.days
        )
        programs.append(copy)
        return copy
    }

    /// Saves a program as a new template with a name + visibility. The program is
    /// unchanged; the template appears in Browse templates under My templates.
    func saveAsTemplate(
        _ program: MockData.Program,
        name: String,
        visibility: MockData.TemplateVisibility
    ) {
        let template = MockData.ProgramTemplate(
            name: name.isEmpty ? program.name : name,
            category: .general,
            description: "Saved from “\(program.name)”.",
            goal: program.goal,
            microcycleLength: program.microcycleLength,
            mesocycleLengthMicrocycles: program.mesocycleLengthMicrocycles,
            visibility: visibility,
            ownerIsMe: true,
            rating: "—",
            days: program.days
        )
        templates.append(template)
    }
}
