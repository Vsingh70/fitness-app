//
//  WorkoutsView.swift
//  GymApp
//
//  Workouts tab: the current-microcycle strip, today's scheduled card (the active
//  program's live rotation slot), and the recent history list. The landing card
//  mirrors the shipped web Workouts hub "Train" section — reading the active
//  program's rotation position from the shared store, not mock data.
//

import SwiftUI

struct WorkoutsView: View {
    @Environment(\.editorialAccent) private var accent
    @Environment(AppNavigator.self) private var navigator
    @Environment(ProgramsStore.self) private var programsStore
    @Environment(WorkoutsStore.self) private var workoutsStore
    @State private var path: [Route] = []
    @State private var isStarting = false

    /// Routes reachable from the Workouts tab.
    enum Route: Hashable {
        case activeSession
        case summary(sessionID: UUID)
        case exerciseDetail
        case programs
        case programChooser
        case programEditor
        case programTemplates
        case templateDetail
        case programDay(dayIndex: Int)
        case calendar
    }

    var body: some View {
        NavigationStack(path: $path) {
            ScrollView {
                VStack(alignment: .leading, spacing: 0) {
                    ScreenHeader(title: "Workouts") {
                        HStack(spacing: 10) {
                            NavigationLink(value: Route.calendar) {
                                Image(systemName: "calendar")
                                    .font(.system(size: 17)).foregroundStyle(.ink)
                                    .frame(width: 38, height: 38)
                                    .overlay(Circle().stroke(Color.ink, lineWidth: 1))
                            }
                            .buttonStyle(.plain)
                            NavigationLink(value: Route.programs) {
                                Image(systemName: "list.bullet.rectangle")
                                    .font(.system(size: 17)).foregroundStyle(.ink)
                                    .frame(width: 38, height: 38)
                                    .overlay(Circle().stroke(Color.ink, lineWidth: 1))
                            }
                            .buttonStyle(.plain)
                        }
                    }
                    microcycleStrip
                    scheduledCard
                    history
                }
                .padding(.bottom, 24)
            }
            .background(Color.bg)
            .scrollIndicators(.hidden)
            .navigationDestination(for: Route.self) { route in
                switch route {
                case .activeSession:   ActiveSessionView()
                case .summary:         SessionSummaryView()
                case .exerciseDetail:  ExerciseDetailView()
                case .programs:        ProgramsRootView()
                case .programChooser:  ProgramChooserView()
                case .programEditor:   ProgramEditorView()
                case .programTemplates: TemplatesBrowseView()
                case .templateDetail:  TemplateDetailView()
                case let .programDay(dayIndex): ProgramDayView(dayIndex: dayIndex)
                case .calendar:        CalendarView()
                }
            }
        }
        .onChange(of: navigator.pendingWorkoutsLink) { _, link in
            consume(link)
        }
        .onAppear { consume(navigator.pendingWorkoutsLink) }
        .environment(programsStore)
        .environment(\.programNavigate) { path.append($0) }
        .environment(\.programPopToOverview) {
            // Drop everything above the programs overview (the spine).
            if let i = path.firstIndex(of: .programs) {
                path.removeSubrange((i + 1)..<path.count)
            } else {
                path.removeAll()
            }
        }
    }

    /// Drain a cross-tab deep link queued by another surface (e.g. an Insights
    /// card). Pushes the matching route onto this tab's stack and clears the
    /// pending link so it fires once.
    private func consume(_ link: AppNavigator.WorkoutsDeepLink?) {
        guard let link else { return }
        switch link {
        case .exerciseDetail:
            if path.last != .exerciseDetail { path.append(.exerciseDetail) }
        case .programs:
            if path.last != .programs { path.append(.programs) }
        }
        navigator.pendingWorkoutsLink = nil
    }

    // MARK: Microcycle strip (current rotation context)

    /// The active program's microcycle laid out in rotation order, with the
    /// current slot marked. Under pure rotation there are no weekday-pinned days,
    /// so this replaces the old hardcoded M/T/W strip. Hidden when there's no
    /// active program / no slots.
    @ViewBuilder
    private var microcycleStrip: some View {
        let slots = workoutsStore.microcycleSlots
        if !slots.isEmpty {
            HStack(spacing: 6) {
                ForEach(slots) { slot in
                    VStack(spacing: 2) {
                        Text(slot.isRest ? "Rest" : slot.name)
                            .font(.system(size: 9, weight: .semibold))
                            .lineLimit(1)
                            .minimumScaleFactor(0.7)
                    }
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 10)
                    .foregroundStyle(slotColor(slot))
                    .background {
                        if slot.isCurrent {
                            RoundedRectangle(cornerRadius: 2).fill(Color.ink)
                        } else {
                            RoundedRectangle(cornerRadius: 2).stroke(Color.hairline, lineWidth: 1)
                        }
                    }
                }
            }
            .padding(.horizontal, 16)
            .padding(.bottom, 24)
        }
    }

    private func slotColor(_ slot: WorkoutsStore.MicrocycleSlot) -> Color {
        if slot.isCurrent { return .bg }
        if slot.isRest { return .ink3 }
        return .ink
    }

    // MARK: Scheduled card (live rotation slot — mirrors web "Train")

    @ViewBuilder
    private var scheduledCard: some View {
        VStack(alignment: .leading, spacing: 14) {
            SectionHeaderLarge(title: "Today · scheduled", trailing: "Calendar")
            if workoutsStore.activeProgram == nil {
                noActiveProgramCard
            } else if workoutsStore.isRestSlot {
                restSlotCard
            } else if let slot = workoutsStore.todaySlot {
                trainingSlotCard(slot)
            } else {
                emptyProgramCard
            }
        }
        .padding(.horizontal, 20)
        .padding(.bottom, 24)
    }

    private func trainingSlotCard(_ slot: MockData.ProgramDay) -> some View {
        HairlineCard {
            VStack(alignment: .leading, spacing: 0) {
                HStack {
                    Text(scheduledKicker)
                        .font(.system(size: 11, weight: .semibold))
                        .textCase(.uppercase).tracking(1.2)
                        .foregroundStyle(accent)
                    Spacer()
                    if let cycle = workoutsStore.microcycleLabel {
                        Text(cycle)
                            .font(.system(size: 10, weight: .semibold))
                            .textCase(.uppercase).tracking(1.0)
                            .foregroundStyle(.ink3)
                    }
                }
                Text(slot.name).font(.titleSerif).foregroundStyle(.ink).padding(.top, 4)
                HStack(spacing: 16) {
                    metaStat("\(slot.exercises.count)", slot.exercises.count == 1 ? "exercise" : "exercises")
                    if workoutsStore.todayEstimatedMinutes > 0 {
                        metaStat("~\(workoutsStore.todayEstimatedMinutes)", "min")
                    }
                    if workoutsStore.todaySetCount > 0 {
                        metaStat("\(workoutsStore.todaySetCount)", "sets")
                    }
                    if workoutsStore.inDeload {
                        Text("Deload")
                            .font(.system(size: 10, weight: .semibold))
                            .textCase(.uppercase).tracking(1.0)
                            .foregroundStyle(.warning)
                            .padding(.horizontal, 9)
                            .frame(height: 22)
                            .overlay(Capsule().stroke(Color.warning.opacity(0.45), lineWidth: 1))
                    }
                }
                .padding(.top, 8)
                if !workoutsStore.todayExerciseSummary.isEmpty {
                    Text(workoutsStore.todayExerciseSummary)
                        .font(.footnote).foregroundStyle(.ink3)
                        .lineLimit(1)
                        .padding(.top, 6)
                }
                Button {
                    startWorkout()
                } label: {
                    Label(isStarting ? "Starting…" : "Start workout", systemImage: "play.fill")
                }
                .buttonStyle(.editorialPrimary)
                .disabled(isStarting)
                .padding(.top, 14)
            }
        }
    }

    private var restSlotCard: some View {
        HairlineCard {
            VStack(alignment: .leading, spacing: 0) {
                Text("Today · Rest")
                    .font(.system(size: 11, weight: .semibold))
                    .textCase(.uppercase).tracking(1.2)
                    .foregroundStyle(.ink3)
                Text("Rest day")
                    .font(.titleSerif).italic().foregroundStyle(.ink2)
                    .padding(.top, 4)
                if let next = workoutsStore.nextTrainingName {
                    Text("Recover today. Next up: \(next). Or start an empty workout if you’re feeling it.")
                        .font(.footnote).foregroundStyle(.ink2)
                        .fixedSize(horizontal: false, vertical: true)
                        .padding(.top, 4)
                } else {
                    Text("Recover today, or start an empty workout if you’re feeling it.")
                        .font(.footnote).foregroundStyle(.ink2)
                        .fixedSize(horizontal: false, vertical: true)
                        .padding(.top, 4)
                }
                Button {
                    startWorkout()
                } label: {
                    Label(isStarting ? "Starting…" : "Start empty workout", systemImage: "play.fill")
                }
                .buttonStyle(.editorialSecondary)
                .disabled(isStarting)
                .padding(.top, 14)
            }
        }
    }

    private var noActiveProgramCard: some View {
        HairlineCard {
            VStack(alignment: .leading, spacing: 0) {
                Text("Today")
                    .font(.system(size: 11, weight: .semibold))
                    .textCase(.uppercase).tracking(1.2)
                    .foregroundStyle(.ink3)
                Text("No active program")
                    .font(.titleSerif).foregroundStyle(.ink)
                    .padding(.top, 4)
                Text("Pick a program to drive your sessions, or start an empty workout right now.")
                    .font(.footnote).foregroundStyle(.ink2)
                    .fixedSize(horizontal: false, vertical: true)
                    .padding(.top, 6)
                Button {
                    startWorkout()
                } label: {
                    Label(isStarting ? "Starting…" : "Start empty workout", systemImage: "play.fill")
                }
                .buttonStyle(.editorialPrimary)
                .disabled(isStarting)
                .padding(.top, 14)
                NavigationLink(value: Route.programs) {
                    Label("Browse programs", systemImage: "arrow.right")
                }
                .buttonStyle(.editorialSecondary)
                .padding(.top, 8)
            }
        }
    }

    private var emptyProgramCard: some View {
        HairlineCard {
            VStack(alignment: .leading, spacing: 0) {
                Text("Today")
                    .font(.system(size: 11, weight: .semibold))
                    .textCase(.uppercase).tracking(1.2)
                    .foregroundStyle(.ink3)
                Text(workoutsStore.activeProgram?.name ?? "Your program")
                    .font(.titleSerif).foregroundStyle(.ink)
                    .padding(.top, 4)
                Text("This program has no slots yet. Add training days in the builder.")
                    .font(.footnote).foregroundStyle(.ink2)
                    .fixedSize(horizontal: false, vertical: true)
                    .padding(.top, 6)
                NavigationLink(value: Route.programs) {
                    Label("Open builder", systemImage: "arrow.right")
                }
                .buttonStyle(.editorialSecondary)
                .padding(.top, 14)
            }
        }
    }

    private var scheduledKicker: String {
        if let name = workoutsStore.activeProgram?.name { return "Today · \(name)" }
        return "Today"
    }

    private func metaStat(_ value: String, _ label: String) -> some View {
        HStack(spacing: 4) {
            Text(value).font(.system(size: 13, weight: .semibold)).monospacedDigit().foregroundStyle(.ink)
            Text(label).font(.footnote).foregroundStyle(.ink2)
        }
    }

    // MARK: History

    @ViewBuilder
    private var history: some View {
        let rows = workoutsStore.sessions
        VStack(alignment: .leading, spacing: 14) {
            SectionHeaderLarge(title: "Recent", trailing: "Calendar")
            VStack(spacing: 0) {
                Rectangle().fill(Color.hairline).frame(height: 1)
                if rows.isEmpty {
                    Text("No sessions logged yet. Start a workout above.")
                        .font(.footnote).foregroundStyle(.ink2)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .padding(.vertical, 16)
                } else {
                    ForEach(rows) { session in
                        NavigationLink(value: Route.summary(sessionID: session.id)) {
                            sessionRow(session)
                        }
                        .buttonStyle(.plain)
                    }
                }
            }
        }
        .padding(.horizontal, 20)
    }

    // MARK: Start

    private func startWorkout() {
        guard !isStarting else { return }
        isStarting = true
        Task {
            let id = await workoutsStore.startSession()
            isStarting = false
            if id != nil { path.append(.activeSession) }
        }
    }

    private func sessionRow(_ session: MockData.Session) -> some View {
        VStack(spacing: 0) {
            HStack(spacing: 14) {
                Image(systemName: "dumbbell")
                    .font(.system(size: 18))
                    .foregroundStyle(.ink)
                    .frame(width: 30)
                VStack(alignment: .leading, spacing: 2) {
                    Text(session.day).font(.headline).foregroundStyle(.ink)
                    Text("\(session.date) · \(session.sets) sets · \(session.duration) · \(session.volume)")
                        .font(.caption).foregroundStyle(.ink2)
                }
                Spacer(minLength: 8)
                if session.prs > 0 {
                    EditorialChip(text: "\(session.prs) PR", tone: .warning, systemImage: "star.fill")
                }
                Image(systemName: "chevron.right")
                    .font(.system(size: 13, weight: .semibold))
                    .foregroundStyle(.ink3)
            }
            .frame(minHeight: 44)
            .padding(.vertical, 6)
            Rectangle().fill(Color.hairline).frame(height: 1)
        }
    }
}

#Preview {
    WorkoutsView()
        .environment(ProgramsStore())
        .environment(WorkoutsStore(preview: true))
        .environment(\.editorialAccent, AccentChoice.clay.color(for: .light))
}
