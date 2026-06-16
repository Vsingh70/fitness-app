//
//  Chips.swift
//  GymApp
//
//  Text-forward chips/badges: uppercase, tracked, colored text. No solid fills.
//  See tasks/redesign/claude-code-editorial-ios.md §3.
//

import SwiftUI

struct EditorialChip: View {
    let text: String
    var tone: Color = .ink2
    var systemImage: String? = nil

    var body: some View {
        HStack(spacing: 4) {
            if let systemImage {
                Image(systemName: systemImage).font(.system(size: 10, weight: .semibold))
            }
            Text(text)
                .font(.system(size: 11, weight: .semibold))
                .textCase(.uppercase)
                .tracking(1.0)
        }
        .foregroundStyle(tone)
    }
}

#Preview {
    HStack(spacing: 16) {
        EditorialChip(text: "2 PR", tone: .warning, systemImage: "star.fill")
        EditorialChip(text: "High", tone: .accent)
        EditorialChip(text: "Synced")
    }
    .padding()
    .background(Color.bg)
}
