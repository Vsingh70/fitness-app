//
//  ProgramsHomeView.swift
//  GymApp
//
//  Programs root (Direction A). First run shows the onboarding (Follow a
//  template vs Build your own). Once onboarded it's the active-program "spine":
//  masthead + mesocycle bar, today's session, this week, then a My programs
//  library with swipe-to-delete / activate / create. Mirrors the nutrition
//  redesign gating pattern.
//

import SwiftUI

struct ProgramsHomeView: View {
    @Environment(SettingsStore.self) private var settings
    @Environment(\.programsStore) private var store
    @Environment(\.editorialAccent) private var accent

    private var programs: [MockData.Program] { store.programs }
    private var activeProgram: MockData.Program? { store.active }

    var body: some View {
        @Bindable var settings = settings

        Group {
            if settings.programSetupMode == nil || programs.isEmpty {
                ProgramsOnboardingView { mode in
                    settings.programSetupMode = mode
                    switch mode {
                    case .template: routeToTemplates()
                    case .build:    routeToBuilder()
                    }
                }
            } else {
                spine
            }
        }
        .background(Color.bg)
        .navigationTitle("")
        .navigationBarTitleDisplayMode(.inline)
    }

    // MARK: Routing (host NavigationStack owns the path; we use the shared enum)

    @Environment(\.programNavigate) private var navigate

    private func routeToTemplates() { navigate(.programTemplates) }
    private func routeToBuilder() { navigate(.programEditor) }

    // MARK: Spine

    private var spine: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 0) {
                if let active = activeProgram {
                    masthead(active)
                    todayCard(active)
                    thisWeek(active)
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

    // MARK: 1 · Masthead + mesocycle bar

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
                    metaPair("Strategy", p.progressionStrategy)
                    metaPair("Frequency", "\(p.daysPerWeek)× / week")
                }
            }
            mesocycleBar(p)
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

    private func mesocycleBar(_ p: MockData.Program) -> some View {
        let current = p.currentWeek ?? 1
        return VStack(alignment: .leading, spacing: 8) {
            HStack(spacing: 4) {
                ForEach(1...p.weeks, id: \.self) { week in
                    mesoCell(week: week, current: current, deload: p.deloadWeek)
                }
            }
            .frame(height: 22)
            Text("Week \(current) of \(p.weeks)")
                .font(.system(size: 11, weight: .semibold))
                .textCase(.uppercase).tracking(1.2)
                .foregroundStyle(.ink2)
        }
    }

    @ViewBuilder
    private func mesoCell(week: Int, current: Int, deload: Int?) -> some View {
        let isDeload = deload == week
        let isCurrent = week == current
        let isDone = week < current
        RoundedRectangle(cornerRadius: 2)
            .fill(isDone ? accent : .clear)
            .overlay {
                if isDeload {
                    RoundedRectangle(cornerRadius: 2)
                        .strokeBorder(style: StrokeStyle(lineWidth: 1, dash: [3, 2]))
                        .foregroundStyle(.ink3)
                } else if isCurrent {
                    RoundedRectangle(cornerRadius: 2)
                        .strokeBorder(accent, lineWidth: 1.5)
                } else if !isDone {
                    RoundedRectangle(cornerRadius: 2)
                        .strokeBorder(Color.hairline, lineWidth: 1)
                }
            }
            .frame(maxWidth: .infinity)
    }

    // MARK: 2 · Today card

    private func todayCard(_ p: MockData.Program) -> some View {
        let day = p.days.first ?? MockData.pplDays[0]
        return VStack(alignment: .leading, spacing: 0) {
            HairlineCard {
                VStack(alignment: .leading, spacing: 0) {
                    Text("Today · Tuesday")
                        .font(.system(size: 11, weight: .semibold))
                        .textCase(.uppercase).tracking(1.2)
                        .foregroundStyle(accent)
                    Text(day.name).font(.titleSerif).foregroundStyle(.ink).padding(.top, 4)
                    Text("\(day.exercises.count) exercises · \(day.muscleSummary)")
                        .font(.footnote).foregroundStyle(.ink2).padding(.top, 4)
                    Button { navigate(.programDay(dayIndex: 0)) } label: {
                        Label("Start workout", systemImage: "play.fill")
                    }
                    .buttonStyle(.editorialPrimary)
                    .padding(.top, 14)
                }
            }
        }
        .padding(.horizontal, 20)
        .padding(.bottom, 24)
    }

    // MARK: 3 · This week

    private func thisWeek(_ p: MockData.Program) -> some View {
        VStack(alignment: .leading, spacing: 14) {
            SectionHeaderLarge(title: "This week", trailing: "Full calendar")
            VStack(spacing: 0) {
                ForEach(Array(MockData.weekStrip.enumerated()), id: \.element.id) { index, wd in
                    weekRow(wd, program: p, index: index, last: index == MockData.weekStrip.count - 1)
                }
            }
        }
        .padding(.horizontal, 20)
        .padding(.bottom, 28)
    }

    private func weekRow(_ wd: MockData.WeekDay, program p: MockData.Program, index: Int, last: Bool) -> some View {
        // Map the week strip onto the program's days for name + muscle summary.
        let day: MockData.ProgramDay? = wd.rest ? nil
            : p.days.indices.contains(index % max(p.days.count, 1)) ? p.days[index % p.days.count] : nil
        return VStack(spacing: 0) {
            Rectangle().fill(Color.hairline).frame(height: 1)
            Button {
                if !wd.rest { navigate(.programDay(dayIndex: index % max(p.days.count, 1))) }
            } label: {
                HStack(alignment: .center, spacing: 14) {
                    Text(dowLong(index))
                        .font(.system(size: 11, weight: .semibold))
                        .textCase(.uppercase).tracking(1.0)
                        .foregroundStyle(.ink3)
                        .frame(width: 34, alignment: .leading)
                    if wd.rest {
                        Text("Rest day")
                            .font(.system(size: 16, design: .serif))
                            .italic()
                            .foregroundStyle(.ink3)
                        Spacer(minLength: 8)
                    } else {
                        VStack(alignment: .leading, spacing: 2) {
                            Text(day?.name ?? wd.tag)
                                .font(.figureSmall)
                                .foregroundStyle(wd.done ? .ink3 : .ink)
                            Text(day?.muscleSummary ?? "")
                                .font(.caption).foregroundStyle(.ink2)
                        }
                        Spacer(minLength: 8)
                        Text("\(day?.exercises.count ?? 0) ex")
                            .font(.caption).monospacedDigit().foregroundStyle(.ink3)
                        statusLabel(wd)
                    }
                }
                .frame(minHeight: 56)
                .padding(.vertical, 6)
                .contentShape(Rectangle())
            }
            .buttonStyle(.plain)
            .disabled(wd.rest)
            if last { Rectangle().fill(Color.hairline).frame(height: 1) }
        }
    }

    @ViewBuilder
    private func statusLabel(_ wd: MockData.WeekDay) -> some View {
        if wd.done {
            Text("Done")
                .font(.system(size: 11, weight: .semibold))
                .textCase(.uppercase).tracking(1.0)
                .foregroundStyle(.ink3)
        } else if wd.today {
            Text("Today")
                .font(.system(size: 11, weight: .semibold))
                .textCase(.uppercase).tracking(1.0)
                .foregroundStyle(accent)
        } else {
            Text("Planned")
                .font(.system(size: 11, weight: .semibold))
                .textCase(.uppercase).tracking(1.0)
                .foregroundStyle(.ink2)
        }
    }

    /// The week strip is a fixed Mon→Sun sequence, so the long weekday label is
    /// derived from the row index rather than the ambiguous single-letter `dow`
    /// (which can't tell Tue from Thu, or Sat from Sun).
    private func dowLong(_ index: Int) -> String {
        let names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        return names.indices.contains(index) ? names[index] : ""
    }

    // MARK: 4 · My programs library (swipe-to-delete)

    private var library: some View {
        VStack(alignment: .leading, spacing: 14) {
            SectionHeaderLarge(title: "My programs", trailing: "+ New program")
                .padding(.horizontal, 20)
                .onTapGesture { routeToBuilder() }
            List {
                ForEach(programs) { program in
                    programRow(program)
                        .listRowInsets(EdgeInsets(top: 0, leading: 20, bottom: 0, trailing: 20))
                        .listRowSeparator(.hidden)
                        .listRowBackground(Color.bg)
                        .swipeActions(edge: .trailing, allowsFullSwipe: false) {
                            Button(role: .destructive) { delete(program) } label: {
                                Label("Delete", systemImage: "trash")
                            }
                        }
                }
                createRow
                    .listRowInsets(EdgeInsets(top: 12, leading: 20, bottom: 0, trailing: 20))
                    .listRowSeparator(.hidden)
                    .listRowBackground(Color.bg)
            }
            .listStyle(.plain)
            .scrollDisabled(true)
            .frame(height: listHeight)
        }
    }

    /// The embedded List is non-scrolling; size it to its content.
    private var listHeight: CGFloat {
        CGFloat(programs.count) * 64 + 70
    }

    private func programRow(_ program: MockData.Program) -> some View {
        VStack(spacing: 0) {
            HStack(spacing: 14) {
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
                    Button("Activate") { activate(program) }
                        .font(.system(size: 11, weight: .semibold))
                        .textCase(.uppercase).tracking(1.0)
                        .foregroundStyle(.ink2)
                        .buttonStyle(.plain)
                }
            }
            .frame(minHeight: 52)
            Rectangle().fill(Color.hairline).frame(height: 1)
        }
    }

    private var createRow: some View {
        Button { routeToBuilder() } label: {
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

    private func programSubtitle(_ p: MockData.Program) -> String {
        if let w = p.currentWeek {
            return "Week \(w) of \(p.weeks) · \(p.goal.lowercased())"
        }
        return "\(p.weeks) weeks · \(p.goal.lowercased())"
    }

    // MARK: Mutations

    private func activate(_ program: MockData.Program) { store.activate(program) }
    private func delete(_ program: MockData.Program) { store.delete(program) }
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

#Preview("Onboarding") {
    NavigationStack {
        ProgramsHomeView()
            .environment(SettingsStore())
            .environment(\.editorialAccent, AccentChoice.clay.color(for: .light))
    }
}

#Preview("Spine") {
    NavigationStack {
        ProgramsHomeView()
            .environment({ let s = SettingsStore(); s.programSetupMode = .template; return s }())
            .environment(\.editorialAccent, AccentChoice.clay.color(for: .light))
    }
}
