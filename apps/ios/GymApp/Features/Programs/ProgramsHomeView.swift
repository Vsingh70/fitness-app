//
//  ProgramsHomeView.swift
//  GymApp
//
//  Programs root: Mine / Templates underline tabs. Mine = user programs (active
//  pinned). Templates = grid of cards. No prototype frame — designed to the
//  editorial system + 08.03 spec.
//

import SwiftUI

struct ProgramsHomeView: View {
    @Environment(\.editorialAccent) private var accent
    @State private var tab = "mine"

    private let gridColumns = [GridItem(.flexible(), spacing: 8), GridItem(.flexible(), spacing: 8)]

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 0) {
                ScreenHeader(title: "Programs") {
                    UnderlineSegmented(
                        selection: $tab,
                        options: [("mine", "Mine"), ("templates", "Templates")],
                        spacing: 16
                    )
                    .fixedSize()
                }

                if tab == "mine" { mine } else { templatesGrid }
            }
            .padding(.bottom, 24)
        }
        .background(Color.bg)
        .scrollIndicators(.hidden)
        .navigationTitle("")
        .navigationBarTitleDisplayMode(.inline)
    }

    // MARK: Mine

    private var mine: some View {
        VStack(spacing: 0) {
            Rectangle().fill(Color.hairline).frame(height: 1)
            ForEach(Array(MockData.myPrograms.enumerated()), id: \.element.id) { index, program in
                NavigationLink(value: WorkoutsView.Route.programEditor) {
                    programRow(program, last: index == MockData.myPrograms.count - 1)
                }
                .buttonStyle(.plain)
            }
        }
        .padding(.horizontal, 20)
    }

    private func programRow(_ program: MockData.Program, last: Bool) -> some View {
        VStack(spacing: 0) {
            HStack(spacing: 14) {
                VStack(alignment: .leading, spacing: 2) {
                    HStack(spacing: 8) {
                        Text(program.name).font(.headline).foregroundStyle(.ink)
                        if program.active {
                            EditorialChip(text: "Active", tone: accent)
                        }
                    }
                    Text(programSubtitle(program)).font(.caption).foregroundStyle(.ink2)
                }
                Spacer(minLength: 8)
                if program.active {
                    Text("Week \(program.currentWeek ?? 1)")
                        .font(.caption).monospacedDigit().foregroundStyle(.ink2)
                } else {
                    Text("Activate")
                        .font(.system(size: 11, weight: .semibold))
                        .textCase(.uppercase).tracking(1.0)
                        .foregroundStyle(accent)
                }
                Image(systemName: "chevron.right")
                    .font(.system(size: 13, weight: .semibold)).foregroundStyle(.ink3)
            }
            .frame(minHeight: 44)
            .padding(.vertical, 10)
            if !last { Rectangle().fill(Color.hairline).frame(height: 1) }
        }
    }

    private func programSubtitle(_ p: MockData.Program) -> String {
        "\(p.goal) · \(p.daysPerWeek) days/wk · \(p.weeks) weeks"
    }

    // MARK: Templates

    private var templatesGrid: some View {
        LazyVGrid(columns: gridColumns, spacing: 8) {
            ForEach(MockData.templates) { template in
                NavigationLink(value: WorkoutsView.Route.templateDetail) {
                    templateCard(template)
                }
                .buttonStyle(.plain)
            }
        }
        .padding(.horizontal, 20)
        .padding(.top, 4)
    }

    private func templateCard(_ t: MockData.Program) -> some View {
        VStack(alignment: .leading, spacing: 0) {
            Text(t.goal.uppercased())
                .font(.system(size: 10, weight: .semibold)).tracking(1.2)
                .foregroundStyle(accent)
            Text(t.name)
                .font(.title2Serif).foregroundStyle(.ink)
                .fixedSize(horizontal: false, vertical: true)
                .padding(.top, 6)
            Spacer(minLength: 12)
            HStack(spacing: 10) {
                metaPair("\(t.daysPerWeek)", "days/wk")
                metaPair("\(t.weeks)", "weeks")
            }
            .padding(.top, 12)
        }
        .frame(maxWidth: .infinity, minHeight: 132, alignment: .topLeading)
        .padding(14)
        .overlay(RoundedRectangle(cornerRadius: 4).stroke(Color.hairline, lineWidth: 1))
    }

    private func metaPair(_ value: String, _ label: String) -> some View {
        HStack(spacing: 3) {
            Text(value).font(.system(size: 13, weight: .semibold)).monospacedDigit().foregroundStyle(.ink)
            Text(label).font(.caption2).foregroundStyle(.ink2)
        }
    }
}

#Preview {
    NavigationStack {
        ProgramsHomeView().environment(\.editorialAccent, AccentChoice.clay.color(for: .light))
    }
}
