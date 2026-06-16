//
//  StatTile.swift
//  GymApp
//
//  Figure-led stat: top hairline, kicker label, big serif value with sans unit,
//  optional muted delta. See tasks/redesign/claude-code-editorial-ios.md §3.
//

import SwiftUI

enum StatDelta: Equatable {
    case up(String)
    case down(String)
    case neutral(String)

    var text: String {
        switch self {
        case .up(let s), .down(let s), .neutral(let s): return s
        }
    }
    var color: Color {
        switch self {
        case .up:      return .success
        case .down:    return .destructive
        case .neutral: return .ink2
        }
    }
}

struct StatTile: View {
    let label: String
    let value: String
    var unit: String? = nil
    var delta: StatDelta? = nil

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            Rectangle().fill(Color.hairline).frame(height: 1)

            Text(label).kicker().padding(.top, 12)

            HStack(alignment: .firstTextBaseline, spacing: 3) {
                Text(value)
                    .font(.figure)
                    .monospacedDigit()
                    .foregroundStyle(.ink)
                if let unit {
                    Text(unit)
                        .font(.footnote)
                        .foregroundStyle(.ink2)
                }
            }
            .padding(.top, 8)

            if let delta {
                Text(delta.text)
                    .font(.caption)
                    .monospacedDigit()
                    .foregroundStyle(delta.color)
                    .padding(.top, 4)
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }
}

#Preview {
    HStack(spacing: 8) {
        StatTile(label: "Sessions", value: "5/6", delta: .up("↑ on pace"))
        StatTile(label: "Sets", value: "96", delta: .up("↑ 11"))
        StatTile(label: "Tonnage", value: "23k", unit: "kg", delta: .up("↑ 6%"))
    }
    .padding()
    .background(Color.bg)
}
