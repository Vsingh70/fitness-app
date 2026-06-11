//
//  GroupedRow.swift
//  GymApp
//
//  Grouped-list row: transparent, thin monochrome leading glyph (never a colored
//  icon tile), title + optional detail, trailing accessory, full-width hairline
//  separator. See tasks/claude-code-editorial-ios.md §3.
//

import SwiftUI

/// What sits at the trailing edge of a row.
enum RowAccessory {
    case chevron
    case detail(String)
    case none
}

struct GroupedRow<Trailing: View>: View {
    var systemImage: String? = nil
    let title: String
    var titleColor: Color = .ink
    var detail: String? = nil
    var showsSeparator: Bool = true
    @ViewBuilder var trailing: Trailing

    var body: some View {
        VStack(spacing: 0) {
            HStack(spacing: 14) {
                if let systemImage {
                    Image(systemName: systemImage)
                        .font(.system(size: 16, weight: .regular))
                        .foregroundStyle(.ink)
                        .frame(width: 24, height: 24)
                }
                Text(title).font(.bodyText).foregroundStyle(titleColor)
                Spacer(minLength: 8)
                if let detail {
                    Text(detail).font(.system(size: 15)).foregroundStyle(.ink2)
                        .monospacedDigit()
                }
                trailing
            }
            .frame(minHeight: 44)
            .padding(.vertical, 6)

            if showsSeparator {
                Rectangle().fill(Color.hairline).frame(height: 1)
            }
        }
    }
}

extension GroupedRow where Trailing == EmptyView {
    init(
        systemImage: String? = nil,
        title: String,
        titleColor: Color = .ink,
        detail: String? = nil,
        accessory: RowAccessory = .none,
        showsSeparator: Bool = true
    ) {
        self.init(
            systemImage: systemImage,
            title: title,
            titleColor: titleColor,
            detail: accessoryDetail(accessory) ?? detail,
            showsSeparator: showsSeparator
        ) {
            EmptyView()
        }
    }
}

/// Convenience trailing chevron wrapper.
struct ChevronRow: View {
    var systemImage: String? = nil
    let title: String
    var detail: String? = nil
    var showsSeparator: Bool = true

    var body: some View {
        GroupedRow(
            systemImage: systemImage,
            title: title,
            detail: detail,
            showsSeparator: showsSeparator
        ) {
            Image(systemName: "chevron.right")
                .font(.system(size: 13, weight: .semibold))
                .foregroundStyle(.ink3)
        }
    }
}

private func accessoryDetail(_ accessory: RowAccessory) -> String? {
    if case .detail(let s) = accessory { return s }
    return nil
}
