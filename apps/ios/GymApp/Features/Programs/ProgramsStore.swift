//
//  ProgramsStore.swift
//  GymApp
//
//  Live, API-backed store for the Programs feature. Loads the user's programs
//  and the template gallery from the v1 API and maps them into the Phase-1 view
//  structs in `MockData.swift` so the screens never change — only their data
//  source does.
//
//  Design notes:
//  - Injected with an `APIClient` + `AuthService`. When those are nil (SwiftUI
//    previews), the store stays offline and seeds from `MockData` so previews
//    still render.
//  - The view-facing methods the Phase-1 screens already call (`activate`,
//    `deactivate`, `delete`, `duplicate`, `saveAsTemplate`, `adopt`) keep their
//    synchronous signatures; each applies an optimistic local change and kicks a
//    `Task` that round-trips to the server and reloads. The screens are unchanged.
//  - Server ids live in side maps keyed by the view structs' `UUID`s so mutations
//    can target the right resource without leaking ids into the view layer.
//  - Never crashes on a network/decode error: failures land in `loadState` and
//    are surfaced as an inline retry in the spine/root.
//

import SwiftUI

@MainActor
@Observable
final class ProgramsStore {

    /// Coarse load lifecycle for the initial program list. Mutations reuse it via
    /// a refresh; the views render a quiet spinner / inline retry off this.
    enum LoadState: Equatable {
        case idle
        case loading
        case loaded
        case failed(String)
    }

    // MARK: View-facing state (the screens read these unchanged)

    var programs: [MockData.Program]
    /// The template gallery — curated + the user's own saved templates.
    var templates: [MockData.ProgramTemplate]

    private(set) var loadState: LoadState = .idle

    // MARK: Dependencies

    private let client: APIClient?
    private let auth: AuthService?

    // MARK: Server-id maps (view UUID → backend id)

    private var programServerID: [UUID: String] = [:]
    private var slotServerID: [UUID: String] = [:]
    private var templateSlug: [UUID: String] = [:]

    /// One-time exercise library lookup (id → name/muscle) so programmed
    /// exercises, which carry only `exercise_id`, render a real label.
    private var exerciseNames: [String: (name: String, muscle: String)] = [:]
    private var exerciseLibraryLoaded = false

    // MARK: Init

    /// Live init — used by the app shell.
    init(client: APIClient, auth: AuthService) {
        self.client = client
        self.auth = auth
        self.programs = []
        self.templates = []
    }

    /// Offline init — used by SwiftUI previews. Seeds from `MockData` so the
    /// canvases keep rendering without a network.
    init(
        programs: [MockData.Program] = MockData.myPrograms,
        templates: [MockData.ProgramTemplate] = MockData.templates
    ) {
        self.client = nil
        self.auth = nil
        self.programs = programs
        self.templates = templates
        self.loadState = .loaded
    }

    var active: MockData.Program? { programs.first { $0.active } }

    /// True once the first load has resolved (success or failure). The root uses
    /// this so it doesn't flash onboarding while the live list is still in flight.
    var hasResolved: Bool {
        switch loadState {
        case .loaded, .failed: return true
        case .idle, .loading: return false
        }
    }

    // MARK: - Load

    /// Fetch the program list (and templates) from the API and map into the
    /// view structs. No-op offline (previews) beyond the seeded state.
    func load() async {
        guard let client else { return }
        await auth?.ensureSignedIn()
        loadState = .loading
        do {
            await loadExerciseLibraryIfNeeded()

            let list: APIProgramList = try await client.request(.get, "/programs")
            // The list rows are light; fetch each full program so the spine and
            // builder have the days/exercises they render.
            var mapped: [MockData.Program] = []
            var newProgramIDs: [UUID: String] = [:]
            var newSlotIDs: [UUID: String] = [:]
            for row in list.items {
                if let full: APIProgram = try? await client.request(.get, "/programs/\(row.id)") {
                    let program = mapProgram(full, into: &newSlotIDs)
                    newProgramIDs[program.id] = full.id
                    mapped.append(program)
                } else {
                    let program = mapListItem(row)
                    newProgramIDs[program.id] = row.id
                    mapped.append(program)
                }
            }
            programServerID = newProgramIDs
            slotServerID = newSlotIDs
            programs = mapped

            await loadTemplatesInternal()
            loadState = .loaded
        } catch {
            loadState = .failed(Self.message(for: error))
        }
    }

    /// Refresh templates only (the browse view can call this). Returns the mapped
    /// list and also updates `templates`.
    @discardableResult
    func templates() async -> [MockData.ProgramTemplate] {
        await loadTemplatesInternal()
        return templates
    }

    private func loadTemplatesInternal() async {
        guard let client else { return }
        do {
            let list: APITemplateList = try await client.request(.get, "/program-templates")
            var mapped: [MockData.ProgramTemplate] = []
            var slugs: [UUID: String] = [:]
            for item in list.items {
                let t = mapTemplate(item)
                slugs[t.id] = item.slug
                mapped.append(t)
            }
            templateSlug = slugs
            templates = mapped
        } catch {
            // Leave any previously-loaded templates in place; the gallery is
            // secondary to the spine.
        }
    }

    private func loadExerciseLibraryIfNeeded() async {
        guard let client, !exerciseLibraryLoaded else { return }
        var cursor: String?
        var names: [String: (name: String, muscle: String)] = [:]
        // Bounded paging (≈3 pages of 200). Best-effort: a failure just means
        // exercises render by their id-derived placeholder.
        for _ in 0..<8 {
            let path = "/exercises?limit=200" + (cursor.map { "&cursor=\($0)" } ?? "")
            guard let page: APIExerciseList = try? await client.request(.get, path) else { break }
            for ex in page.items {
                names[ex.id] = (ex.name, (ex.primaryMuscle ?? "").replacingOccurrences(of: "_", with: " "))
            }
            cursor = page.nextCursor
            if cursor == nil { break }
        }
        if !names.isEmpty {
            exerciseNames = names
            exerciseLibraryLoaded = true
        }
    }

    // MARK: - Position

    /// `GET /v1/programs/{id}/position` for the given view-program, if it maps to
    /// a server id. Returns nil offline or when unavailable.
    func position(for program: MockData.Program) async -> APIPosition? {
        guard let client, let id = programServerID[program.id] else { return nil }
        return try? await client.request(.get, "/programs/\(id)/position")
    }

    /// The backend program id for a view-program, if known. Other surfaces (e.g.
    /// the Today command center's start-session) resolve the resource id through
    /// this rather than re-fetching the list.
    func serverID(for program: MockData.Program) -> String? {
        programServerID[program.id]
    }

    // MARK: - Activation

    func activate(_ program: MockData.Program) {
        // Optimistic: exactly one active.
        for i in programs.indices { programs[i].active = false }
        if let i = programs.firstIndex(where: { $0.id == program.id }) {
            programs[i].active = true
        }
        guard let client, let id = programServerID[program.id] else { return }
        Task { [weak self] in
            try? await client.requestVoid(.post, "/programs/\(id)/activate")
            await self?.load()
        }
    }

    /// Deactivates without deleting — the program keeps its position.
    func deactivate(_ program: MockData.Program) {
        if let i = programs.firstIndex(where: { $0.id == program.id }) {
            programs[i].active = false
        }
        guard let client, let id = programServerID[program.id] else { return }
        Task { [weak self] in
            try? await client.requestVoid(.post, "/programs/\(id)/deactivate")
            await self?.load()
        }
    }

    func delete(_ program: MockData.Program) {
        let serverID = programServerID[program.id]
        programs.removeAll { $0.id == program.id }
        guard let client, let id = serverID else { return }
        Task { [weak self] in
            try? await client.requestVoid(.delete, "/programs/\(id)")
            await self?.load()
        }
    }

    // MARK: - Create / duplicate / adopt

    /// Create a blank program on the server, then reload. Offline: appends a
    /// local blank.
    func createEmpty(name: String = "New program", goal: String = "Hypertrophy") {
        guard let client else {
            var blank = MockData.blankProgram
            blank = MockData.Program(
                name: name, goal: goal, intensityMode: .rpe,
                microcycleLength: 1, mesocycleLengthMicrocycles: 4, autoDeload: true,
                days: blank.days
            )
            programs.append(blank)
            return
        }
        Task { [weak self] in
            struct Body: Encodable {
                let name: String
                let goal: String
                let intensityMode: String = "rpe"
            }
            try? await client.requestVoid(
                .post, "/programs",
                body: Body(name: name, goal: Self.goalSlug(goal))
            )
            await self?.load()
        }
    }

    /// Copies a template into a new program via `POST /program-templates/{slug}/copy`.
    /// The new program lands inactive; the user activates it from the spine.
    func copyTemplate(slug: String) {
        guard let client else { return }
        Task { [weak self] in
            try? await client.requestVoid(.post, "/program-templates/\(slug)/copy")
            await self?.load()
        }
    }

    /// Adopt the given template (the Phase-1 screens call this). Resolves the
    /// server slug and copies it; offline it appends a local program.
    func adopt(_ template: MockData.ProgramTemplate) {
        if let client, let slug = templateSlug[template.id] {
            Task { [weak self] in
                try? await client.requestVoid(.post, "/program-templates/\(slug)/copy")
                await self?.load()
            }
            return
        }
        // Offline fallback (previews): mirror the old local behaviour.
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

    /// Forks a program into a new editable, inactive copy.
    @discardableResult
    func duplicate(_ program: MockData.Program) -> MockData.Program {
        let copy = MockData.Program(
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
        guard let client, let id = programServerID[program.id] else { return copy }
        Task { [weak self] in
            try? await client.requestVoid(.post, "/programs/\(id)/duplicate")
            await self?.load()
        }
        return copy
    }

    /// Saves a program as a new template (`POST /programs/{id}/save-as-template`).
    func saveAsTemplate(
        _ program: MockData.Program,
        name: String,
        visibility: MockData.TemplateVisibility
    ) {
        let resolvedName = name.isEmpty ? program.name : name
        // Optimistic local row so the gallery updates immediately.
        let local = MockData.ProgramTemplate(
            name: resolvedName,
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
        templates.append(local)

        guard let client, let id = programServerID[program.id] else { return }
        Task { [weak self] in
            struct Body: Encodable { let name: String; let visibility: String }
            try? await client.requestVoid(
                .post, "/programs/\(id)/save-as-template",
                body: Body(name: resolvedName, visibility: Self.visibilitySlug(visibility))
            )
            await self?.templates()
        }
    }

    // MARK: - Slot / exercise mutations

    /// Append a training slot to a program (`POST /programs/{id}/slots`).
    func addSlot(to program: MockData.Program, name: String, isRest: Bool = false) {
        guard let client, let id = programServerID[program.id] else { return }
        Task { [weak self] in
            struct Body: Encodable { let name: String; let isRestDay: Bool }
            try? await client.requestVoid(
                .post, "/programs/\(id)/slots",
                body: Body(name: name, isRestDay: isRest)
            )
            await self?.load()
        }
    }

    /// Delete a slot (`DELETE /program-slots/{slot_id}`).
    func deleteSlot(_ slot: MockData.ProgramDay) {
        guard let client, let id = slotServerID[slot.id] else { return }
        Task { [weak self] in
            try? await client.requestVoid(.delete, "/program-slots/\(id)")
            await self?.load()
        }
    }

    /// Reorder a program's slots (`POST /programs/{id}/slots/reorder`).
    func reorderSlots(in program: MockData.Program, orderedSlots: [MockData.ProgramDay]) {
        guard let client, let id = programServerID[program.id] else { return }
        let ids = orderedSlots.compactMap { slotServerID[$0.id] }
        guard ids.count == orderedSlots.count else { return }
        Task { [weak self] in
            struct Body: Encodable { let slotIds: [String] }
            try? await client.requestVoid(
                .post, "/programs/\(id)/slots/reorder",
                body: Body(slotIds: ids)
            )
            await self?.load()
        }
    }

    /// Toggle a slot between training / rest (`PATCH /program-slots/{slot_id}`).
    func toggleRest(_ slot: MockData.ProgramDay) {
        guard let client, let id = slotServerID[slot.id] else { return }
        Task { [weak self] in
            struct Body: Encodable { let isRestDay: Bool }
            try? await client.requestVoid(
                .patch, "/program-slots/\(id)",
                body: Body(isRestDay: !slot.isRestDay)
            )
            await self?.load()
        }
    }

    /// Add an exercise to a slot (`POST /program-slots/{slot_id}/exercises`).
    func addExercise(to slot: MockData.ProgramDay, exerciseID: String, sets: Int = 3) {
        guard let client, let id = slotServerID[slot.id] else { return }
        Task { [weak self] in
            struct Body: Encodable { let exerciseId: String; let targetSets: Int }
            try? await client.requestVoid(
                .post, "/program-slots/\(id)/exercises",
                body: Body(exerciseId: exerciseID, targetSets: sets)
            )
            await self?.load()
        }
    }

    // MARK: - Mapping (API → Phase-1 view structs)

    private func mapListItem(_ item: APIProgramListItem) -> MockData.Program {
        MockData.Program(
            name: item.name,
            goal: Self.goalTitle(item.goal),
            intensityMode: .rpe,
            microcycleLength: item.microcycleLength,
            mesocycleLengthMicrocycles: item.mesocycleLengthMicrocycles,
            currentSlotIndex: 0,
            currentRepetition: 1,
            inDeload: false,
            active: item.isActive,
            days: []
        )
    }

    private func mapProgram(_ p: APIProgram, into slotIDs: inout [UUID: String]) -> MockData.Program {
        let days = p.days
            .sorted { $0.slotIndex < $1.slotIndex }
            .map { slot -> MockData.ProgramDay in
                let day = mapSlot(slot, mode: Self.intensityMode(p.intensityMode))
                slotIDs[day.id] = slot.id
                return day
            }
        return MockData.Program(
            name: p.name,
            goal: Self.goalTitle(p.goal),
            progressionStrategy: Self.progressionTitle(p),
            intensityMode: Self.intensityMode(p.intensityMode),
            microcycleLength: p.microcycleLength,
            mesocycleLengthMicrocycles: p.mesocycleLengthMicrocycles,
            autoDeload: p.autoDeload ?? false,
            currentSlotIndex: 0,
            currentRepetition: 1,
            inDeload: false,
            active: p.isActive,
            days: days
        )
    }

    private func mapSlot(_ slot: APIProgramSlot, mode: MockData.IntensityMode) -> MockData.ProgramDay {
        let exercises = slot.exercises
            .sorted { $0.position < $1.position }
            .map { mapExercise($0, mode: mode) }
        return MockData.ProgramDay(
            slotIndex: slot.slotIndex,
            isRestDay: slot.isRestDay,
            name: slot.name ?? (slot.isRestDay ? "Rest" : "Slot \(slot.slotIndex + 1)"),
            muscleSummary: Self.muscleSummary(for: exercises),
            exercises: exercises
        )
    }

    private func mapExercise(_ e: APIProgramExercise, mode: MockData.IntensityMode) -> MockData.ProgramExercise {
        let resolved = exerciseNames[e.exerciseId]
        let repMode: MockData.RepMode = (e.repMode == "target") ? .target : .range
        return MockData.ProgramExercise(
            name: resolved?.name ?? "Exercise",
            muscle: resolved?.muscle ?? "—",
            sets: e.targetSets ?? 0,
            reps: Self.repsString(low: e.targetRepsLow, high: e.targetRepsHigh, repMode: repMode),
            repMode: repMode,
            intensityTarget: Self.intensityTarget(e, mode: mode)
        )
    }

    private func mapTemplate(_ t: APITemplateSummary) -> MockData.ProgramTemplate {
        MockData.ProgramTemplate(
            name: t.name,
            category: Self.category(t.goal),
            description: t.description ?? "",
            goal: Self.goalTitle(t.goal),
            microcycleLength: t.microcycleLength,
            mesocycleLengthMicrocycles: t.mesocycleLengthMicrocycles,
            visibility: Self.visibility(t.visibility),
            ownerIsMe: t.ownerId != nil,
            rating: "—",
            days: []
        )
    }

    // MARK: - Mapping helpers

    private static func repsString(low: Int?, high: Int?, repMode: MockData.RepMode) -> String {
        switch (low, high) {
        case let (l?, h?) where repMode == .range && h != l: return "\(l)–\(h)"
        case let (_, h?): return "\(h)"
        case let (l?, _): return "\(l)"
        default: return "—"
        }
    }

    private static func intensityTarget(_ e: APIProgramExercise, mode: MockData.IntensityMode) -> String {
        switch mode {
        case .rpe:
            if let lo = e.targetRpeLowValue, let hi = e.targetRpeHighValue {
                let l = trimmed(lo), h = trimmed(hi)
                return l == h ? l : "\(l)–\(h)"
            }
            return e.targetRpeHighValue.map(trimmed) ?? "—"
        case .rir:
            switch (e.targetRirLow, e.targetRirHigh) {
            case let (lo?, hi?): return lo == hi ? "\(lo)" : "\(lo)–\(hi)"
            case let (_, hi?): return "\(hi)"
            case let (lo?, _): return "\(lo)"
            default: return "—"
            }
        case .off:
            return ""
        }
    }

    private static func trimmed(_ v: Double) -> String {
        v == v.rounded() ? String(Int(v)) : String(v)
    }

    private static func muscleSummary(for exercises: [MockData.ProgramExercise]) -> String {
        var seen: [String] = []
        for ex in exercises where !ex.muscle.isEmpty && ex.muscle != "—" {
            if !seen.contains(ex.muscle) { seen.append(ex.muscle) }
        }
        return seen.prefix(3).joined(separator: " · ")
    }

    private static func intensityMode(_ raw: String?) -> MockData.IntensityMode {
        switch raw {
        case "rir": return .rir
        case "off": return .off
        default: return .rpe
        }
    }

    private static func progressionTitle(_ p: APIProgram) -> String {
        // Pick the most common per-exercise strategy as the program headline.
        let strategies = p.days.flatMap { $0.exercises }.compactMap { $0.progressionStrategy }
        let pick = strategies.first { $0 != "none" } ?? strategies.first
        switch pick {
        case "linear": return "Linear progression"
        case "double_progression": return "Double progression"
        case "rpe_based": return "RPE-based"
        default: return "Hold load"
        }
    }

    private static func goalTitle(_ raw: String?) -> String {
        switch raw {
        case "hypertrophy": return "Hypertrophy"
        case "strength": return "Strength"
        case "powerbuilding": return "Powerbuilding"
        case "fat_loss": return "Fat loss"
        case "general": return "General"
        case "custom": return "Custom"
        case let other?: return other.capitalized
        case nil: return "General"
        }
    }

    /// Map a display goal back to the API slug for `ProgramCreate`.
    private static func goalSlug(_ title: String) -> String {
        switch title.lowercased() {
        case "hypertrophy": return "hypertrophy"
        case "strength": return "strength"
        case "powerbuilding": return "powerbuilding"
        case "fat loss", "recomp", "cut": return "fat_loss"
        case "general": return "general"
        default: return "general"
        }
    }

    private static func category(_ goal: String?) -> MockData.TemplateCategory {
        switch goal {
        case "strength", "powerbuilding": return .strength
        case "hypertrophy": return .hypertrophy
        default: return .general
        }
    }

    private static func visibility(_ raw: String?) -> MockData.TemplateVisibility {
        switch raw {
        case "private": return .private
        case "shared": return .shared
        default: return .curated
        }
    }

    private static func visibilitySlug(_ v: MockData.TemplateVisibility) -> String {
        switch v {
        case .shared: return "shared"
        default: return "private"
        }
    }

    private static func message(for error: Error) -> String {
        guard let api = error as? APIError else { return "Something went wrong." }
        switch api {
        case .network:
            return "Couldn’t reach the server. Check your connection."
        case .decoding:
            return "We couldn’t read the response from the server."
        case .unauthorized:
            return "Your session expired. Pull to retry."
        case let .server(status, _, message):
            return message ?? "Server error (\(status))."
        case .invalidURL:
            return "Something went wrong."
        }
    }
}
