//
//  TemplatesBrowseView.swift
//  GymApp
//
//  Browse the template gallery (Direction A §6 · design IosTemplates / .pit-*):
//  underline category filters over a single-column list of hairline-separated
//  template rows. Tapping a row routes to the template detail.
//

import SwiftUI

struct TemplatesBrowseView: View {
    @Environment(\.editorialAccent) private var accent
    @Environment(\.programNavigate) private var navigate
    @State private var filter: String = "all"

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
                // pi-head
                VStack(alignment: .leading, spacing: 6) {
                    Text("Programs ›")
                        .font(.system(size: 11, weight: .semibold)).textCase(.uppercase)
                        .tracking(1.6).foregroundStyle(.ink2)
                    Text("Templates")
                        .font(.system(size: 30, weight: .medium, design: .serif))
                        .foregroundStyle(.ink)
                }
                .padding(.horizontal, 22).padding(.top, 10).padding(.bottom, 14)

                // pit-filters
                ScrollView(.horizontal) {
                    UnderlineSegmented(selection: $filter, options: filterOptions, spacing: 16)
                        .padding(.horizontal, 22)
                }
                .scrollIndicators(.hidden)
                .padding(.bottom, 4)

                // pit-tpl list
                LazyVStack(alignment: .leading, spacing: 0) {
                    ForEach(visible) { template in
                        Button { navigate(.templateDetail) } label: {
                            templateRow(template)
                        }
                        .buttonStyle(.plain)
                    }
                }
                .padding(.horizontal, 22)
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
            Text(t.category.rawValue.uppercased() + (t.active ? " · ACTIVE" : ""))
                .font(.system(size: 9, weight: .semibold)).tracking(0.9)
                .foregroundStyle(.ink3)
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
                metaPair("\(t.weeks)", "wk")
                metaPair("\(t.daysPerWeek)", "/wk")
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
            .environment(\.editorialAccent, AccentChoice.clay.color(for: .light))
    }
}
