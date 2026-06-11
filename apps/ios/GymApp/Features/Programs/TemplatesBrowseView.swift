//
//  TemplatesBrowseView.swift
//  GymApp
//
//  Browse the template gallery (Direction A §6): underline category filters
//  (All / Hypertrophy / Strength / Endurance / General) over a gallery of
//  template cards. Tapping a card routes to the template detail.
//

import SwiftUI

struct TemplatesBrowseView: View {
    @Environment(\.editorialAccent) private var accent
    @Environment(\.programNavigate) private var navigate
    @State private var filter: String = "all"

    private let columns = [GridItem(.flexible(), spacing: 10), GridItem(.flexible(), spacing: 10)]

    private var filterOptions: [(String, String)] {
        [("all", "All")] + MockData.TemplateCategory.allCases.map { ($0.rawValue, $0.rawValue) }
    }

    private var visible: [MockData.ProgramTemplate] {
        guard filter != "all" else { return MockData.templates }
        return MockData.templates.filter { $0.category.rawValue == filter }
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 0) {
                Text("Browse templates")
                    .font(.largeTitleSerif).foregroundStyle(.ink)
                    .padding(.horizontal, 24).padding(.top, 8)
                Text("Proven programs you can copy and start this week.")
                    .font(.footnote).foregroundStyle(.ink2)
                    .padding(.horizontal, 24).padding(.top, 6).padding(.bottom, 18)

                ScrollView(.horizontal) {
                    UnderlineSegmented(
                        selection: $filter,
                        options: filterOptions,
                        spacing: 16
                    )
                    .padding(.horizontal, 20)
                }
                .scrollIndicators(.hidden)
                .padding(.bottom, 16)

                LazyVGrid(columns: columns, spacing: 10) {
                    ForEach(visible) { template in
                        Button { navigate(.templateDetail) } label: {
                            templateCard(template)
                        }
                        .buttonStyle(.plain)
                    }
                }
                .padding(.horizontal, 20)
            }
            .padding(.bottom, 28)
        }
        .background(Color.bg)
        .scrollIndicators(.hidden)
        .navigationTitle("")
        .navigationBarTitleDisplayMode(.inline)
    }

    private func templateCard(_ t: MockData.ProgramTemplate) -> some View {
        VStack(alignment: .leading, spacing: 0) {
            HStack(spacing: 6) {
                Text(t.category.rawValue.uppercased())
                    .font(.system(size: 10, weight: .semibold)).tracking(1.2)
                    .foregroundStyle(accent)
                if t.active {
                    Text("· Active")
                        .font(.system(size: 10, weight: .semibold)).tracking(1.0)
                        .foregroundStyle(.ink3)
                }
            }
            Text(t.name)
                .font(.title2Serif).foregroundStyle(.ink)
                .fixedSize(horizontal: false, vertical: true)
                .padding(.top, 6)
            Text(t.description)
                .font(.caption).foregroundStyle(.ink2)
                .lineLimit(3)
                .fixedSize(horizontal: false, vertical: true)
                .padding(.top, 6)
            Spacer(minLength: 10)
            HStack(spacing: 10) {
                metaPair("\(t.daysPerWeek)", "days/wk")
                metaPair("\(t.weeks)", "weeks")
            }
            .padding(.top, 10)
        }
        .frame(maxWidth: .infinity, minHeight: 176, alignment: .topLeading)
        .padding(14)
        .overlay(
            RoundedRectangle(cornerRadius: 4)
                .stroke(t.active ? accent.opacity(0.5) : Color.hairline, lineWidth: 1)
        )
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
        TemplatesBrowseView()
            .environment(\.editorialAccent, AccentChoice.clay.color(for: .light))
    }
}
