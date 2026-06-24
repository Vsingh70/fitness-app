//
//  TemplatesBrowseView.swift
//  GymApp
//
//  Browse the template gallery (Direction A §7): underline category filters over
//  grouped sections — Curated, My templates, Shared by partners. Template meta is
//  microcycle length + mesocycle length (not weeks/days). Reads the store so
//  user-saved templates appear. Tapping a row routes to the template detail.
//

import SwiftUI

struct TemplatesBrowseView: View {
    @Environment(ProgramsStore.self) private var store
    @Environment(\.editorialAccent) private var accent
    @Environment(\.programNavigate) private var navigate
    @State private var filter: String = "all"

    private var filterOptions: [(String, String)] {
        [("all", "All")] + MockData.TemplateCategory.allCases.map { ($0.rawValue, $0.rawValue) }
    }

    private var visible: [MockData.ProgramTemplate] {
        guard filter != "all" else { return store.templates }
        return store.templates.filter { $0.category.rawValue == filter }
    }

    /// Browse groups (Direction A §7): Curated, My templates (the user's own,
    /// private + shared), Shared by partners.
    private var groups: [(title: String, items: [MockData.ProgramTemplate])] {
        let curated = visible.filter { $0.visibility == .curated }
        let mine = visible.filter { $0.ownerIsMe }
        let shared = visible.filter { $0.visibility == .shared && !$0.ownerIsMe }
        return [
            ("Curated", curated),
            ("My templates", mine),
            ("Shared by partners", shared),
        ].filter { !$0.items.isEmpty }
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 0) {
                VStack(alignment: .leading, spacing: 6) {
                    Text("Programs ›")
                        .font(.system(size: 11, weight: .semibold)).textCase(.uppercase)
                        .tracking(1.6).foregroundStyle(.ink2)
                    Text("Templates")
                        .font(.system(size: 30, weight: .medium, design: .serif))
                        .foregroundStyle(.ink)
                }
                .padding(.horizontal, 22).padding(.top, 10).padding(.bottom, 14)

                ScrollView(.horizontal) {
                    UnderlineSegmented(selection: $filter, options: filterOptions, spacing: 16)
                        .padding(.horizontal, 22)
                }
                .scrollIndicators(.hidden)
                .padding(.bottom, 4)

                LazyVStack(alignment: .leading, spacing: 0) {
                    ForEach(groups, id: \.title) { group in
                        Text(group.title).kicker()
                            .padding(.horizontal, 22)
                            .padding(.top, 22).padding(.bottom, 4)
                        ForEach(group.items) { template in
                            Button { navigate(.templateDetail) } label: {
                                templateRow(template)
                            }
                            .buttonStyle(.plain)
                            .padding(.horizontal, 22)
                        }
                    }
                }
            }
            .padding(.bottom, 28)
        }
        .background(Color.bg)
        .scrollIndicators(.hidden)
        .navigationTitle("")
        .navigationBarTitleDisplayMode(.inline)
    }

    private func templateRow(_ t: MockData.ProgramTemplate) -> some View {
        VStack(alignment: .leading, spacing: 0) {
            HStack(spacing: 6) {
                Text(t.category.rawValue.uppercased() + (t.active ? " · ACTIVE" : ""))
                    .font(.system(size: 9, weight: .semibold)).tracking(0.9)
                    .foregroundStyle(.ink3)
                if t.ownerIsMe {
                    Text("· \(t.visibility.title.uppercased())")
                        .font(.system(size: 9, weight: .semibold)).tracking(0.9)
                        .foregroundStyle(accent)
                }
            }
            Text(t.name)
                .font(.system(size: 19, weight: .medium, design: .serif))
                .foregroundStyle(t.active ? accent : Color.ink)
                .fixedSize(horizontal: false, vertical: true)
                .padding(.top, 3).padding(.bottom, 5)
            Text(t.description)
                .font(.system(size: 12)).foregroundStyle(.ink2)
                .lineSpacing(2).lineLimit(3)
                .fixedSize(horizontal: false, vertical: true)
            HStack(spacing: 14) {
                metaPair("\(t.microcycleLength)", "slot cycle")
                metaPair("\(t.mesocycleLengthMicrocycles)", "microcycles")
            }
            .padding(.top, 8)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(.vertical, 16)
        .overlay(alignment: .bottom) { Rectangle().fill(Color.hairline).frame(height: 1) }
    }

    private func metaPair(_ value: String, _ label: String) -> some View {
        HStack(spacing: 3) {
            Text(value)
                .font(.system(size: 11, weight: .medium, design: .serif))
                .monospacedDigit().foregroundStyle(.ink2)
            Text(label).font(.system(size: 10)).foregroundStyle(.ink3)
        }
    }
}

#Preview {
    NavigationStack {
        TemplatesBrowseView()
            .environment(ProgramsStore())
            .environment(\.editorialAccent, AccentChoice.clay.color(for: .light))
    }
}
