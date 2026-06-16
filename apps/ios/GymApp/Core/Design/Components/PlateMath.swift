//
//  PlateMath.swift
//  GymApp
//
//  Barbell plate visualization for the active workout. Plates use ink/Label2,
//  not red. See tasks/redesign/claude-code-editorial-ios.md §3 (active workout).
//

import SwiftUI

struct PlateMath: View {
    /// One side of the bar, outer → inner (kg).
    let plates: [Double]
    let caption: String

    var body: some View {
        HStack(spacing: 3) {
            collar
            ForEach(Array(plates.enumerated()), id: \.offset) { _, p in
                plate(p)
            }
            barSegment
            barSegment
            ForEach(Array(plates.reversed().enumerated()), id: \.offset) { _, p in
                plate(p)
            }
            collar
            Text(caption)
                .font(.system(size: 11, design: .monospaced))
                .foregroundStyle(.ink2)
                .padding(.leading, 8)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 12)
        .overlay(alignment: .bottom) {
            Rectangle().fill(Color.hairline).frame(height: 1)
        }
    }

    private var collar: some View {
        RoundedRectangle(cornerRadius: 1).fill(Color.ink2).frame(width: 4, height: 14)
    }

    private var barSegment: some View {
        RoundedRectangle(cornerRadius: 1).fill(Color.ink2).frame(width: 24, height: 6)
    }

    private func plate(_ p: Double) -> some View {
        Text(p.formatted(.number.precision(.fractionLength(0))))
            .font(.system(size: 9, weight: .medium, design: .serif))
            .foregroundStyle(.bg)
            .frame(width: 10 + p / 2, height: 8 + p * 1.4)
            .background(RoundedRectangle(cornerRadius: 2).fill(p >= 20 ? Color.ink : Color.ink2))
    }
}
