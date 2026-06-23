//
//  ProgramsStore.swift
//  GymApp
//
//  Shared in-memory library of the user's programs for the visual prototype.
//  Activate / delete / create / "use this template" mutate it; the overview,
//  builder and template flow all read the same instance. No persistence.
//

import SwiftUI

@MainActor
@Observable
final class ProgramsStore {
    var programs: [MockData.Program]

    init(programs: [MockData.Program] = MockData.myPrograms) {
        self.programs = programs
    }

    var active: MockData.Program? { programs.first { $0.active } }

    func activate(_ program: MockData.Program) {
        for i in programs.indices { programs[i].active = false }
        if let i = programs.firstIndex(where: { $0.id == program.id }) {
            programs[i].active = true
        }
    }

    func delete(_ program: MockData.Program) {
        programs.removeAll { $0.id == program.id }
    }

    /// Copies a template into a new active program (mirrors "Use this template").
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
        activate(new)
    }
}
