//
//  WorkoutsView.swift
//  GymApp
//
//  Workouts tab: week strip, today's scheduled card, recent history list.
//  Mirrors ScreenWorkoutsIOS.
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
                    weekStrip
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

    // MARK: Week strip

    private var weekStrip: some View {
        HStack(spacing: 6) {
            ForEach(MockData.weekStrip) { day in
                VStack(spacing: 2) {
                    Text(day.dow)
                        .font(.system(size: 10, weight: .semibold))
                        .textCase(.uppercase)
                        .opacity(0.7)
                    Text("\(day.date)")
                        .font(.figureSmall)
                        .monospacedDigit()
                    Text(day.tag)
                        .font(.system(size: 9, weight: .semibold))
                        .padding(.top, 2)
                        .opacity(0.85)
                }
                .frame(maxWidth: .infinity)
                .padding(.vertical, 8)
                .foregroundStyle(dayColor(day))
                .background {
                    if day.today {
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

    private func dayColor(_ day: MockData.WeekDay) -> Color {
        if day.today { return .bg }
        if day.done { return accent }
        if day.rest { return .ink3 }
        return .ink
    }

    // MARK: Scheduled card

    private var scheduledCard: some View {
        let w = MockData.scheduledToday
        return VStack(alignment: .leading, spacing: 14) {
            SectionHeaderLarge(title: "Today · scheduled", trailing: "Reschedule")
            HairlineCard {
                VStack(alignment: .leading, spacing: 0) {
                    Text("Push A · Week 4")
                        .font(.system(size: 11, weight: .semibold))
                        .textCase(.uppercase)
                        .tracking(1.2)
                        .foregroundStyle(accent)
                    Text(w.day).font(.titleSerif).foregroundStyle(.ink).padding(.top, 4)
                    Text("\(w.exercises) exercises · ~\(w.minutes) min · \(w.sets) sets")
                        .font(.footnote).foregroundStyle(.ink2).padding(.top, 4)
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
        .padding(.horizontal, 20)
        .padding(.bottom, 24)
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
