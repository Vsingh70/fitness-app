//
//  Cards.swift
//  GymApp
//
//  Editorial surfaces — flat, hairline-delimited, no shadow.
//  See tasks/claude-code-editorial-ios.md §3.
//

import SwiftUI

/// Flat card: surface2 fill, 4pt radius, 1pt hairline border, no shadow.
/// Use for genuinely elevated content; prefer ``HairlineCard`` for grouped rows.
struct EditorialCard<Content: View>: View {
    var padding: CGFloat = 16
    @ViewBuilder var content: Content

    var body: some View {
        content
            .padding(padding)
            .background(Color.surface2)
            .overlay(
                RoundedRectangle(cornerRadius: 4)
                    .stroke(Color.hairline, lineWidth: 1)
            )
            .clipShape(RoundedRectangle(cornerRadius: 4))
    }
}

/// Transparent card delimited by full-width top + bottom hairlines — the
/// prototype's `.ios-card`. The editorial default for list-like groupings.
struct HairlineCard<Content: View>: View {
    var padding: CGFloat = 16
    @ViewBuilder var content: Content

    var body: some View {
        content
            .padding(.vertical, padding)
            .frame(maxWidth: .infinity, alignment: .leading)
            .overlay(alignment: .top) { Divider().overlay(Color.hairline) }
            .overlay(alignment: .bottom) { Divider().overlay(Color.hairline) }
    }
}

/// Large serif section header with an optional trailing "more" link (uppercase,
/// tracked) sitting on a bottom hairline rule. Matches `.ios-section-h-large`.
struct SectionHeaderLarge: View {
    let title: String
    var trailing: String? = nil

    var body: some View {
        HStack(alignment: .lastTextBaseline) {
            Text(title).font(.titleSerif).foregroundStyle(.ink)
            Spacer()
            if let trailing {
                Text(trailing)
                    .font(.system(size: 11, weight: .semibold))
                    .textCase(.uppercase)
                    .tracking(1.2)
                    .foregroundStyle(.ink2)
            }
        }
        .padding(.bottom, 12)
        .overlay(alignment: .bottom) { Divider().overlay(Color.hairline) }
    }
}

/// Small uppercase section label. Matches `.ios-section-h`.
struct SectionHeader: View {
    let title: String
    var body: some View {
        Text(title).kicker().frame(maxWidth: .infinity, alignment: .leading)
    }
}
