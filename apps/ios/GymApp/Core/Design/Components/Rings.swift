//
//  Rings.swift
//  GymApp
//
//  Thin-stroke progress rings. Track at low opacity, rounded cap.
//  See tasks/redesign/claude-code-editorial-ios.md §3.
//

import SwiftUI

/// A single thin progress ring.
struct ActivityRing: View {
    var value: Double
    var size: CGFloat = 80
    var lineWidth: CGFloat = 8
    /// Defaults to the environment accent; pass an explicit tone for macro rings.
    var color: Color? = nil

    @Environment(\.editorialAccent) private var accent

    var body: some View {
        let tint = color ?? accent
        let clamped = min(max(value, 0), 1)
        ZStack {
            Circle()
                .stroke(tint.opacity(0.18), lineWidth: lineWidth)
            Circle()
                .trim(from: 0, to: clamped)
                .stroke(tint, style: StrokeStyle(lineWidth: lineWidth, lineCap: .round))
                .rotationEffect(.degrees(-90))
        }
        .frame(width: size, height: size)
    }
}

/// Apple-Fitness-style concentric ring stack (kcal + macros).
struct TripleRing: View {
    /// Outer → inner.
    let rings: [(value: Double, color: Color)]
    var size: CGFloat = 96
    var lineWidth: CGFloat = 9
    var gap: CGFloat = 3

    var body: some View {
        ZStack {
            ForEach(Array(rings.enumerated()), id: \.offset) { index, ring in
                let inset = CGFloat(index) * (lineWidth + gap)
                let clamped = min(max(ring.value, 0), 1)
                ZStack {
                    Circle()
                        .stroke(ring.color.opacity(0.18), lineWidth: lineWidth)
                    Circle()
                        .trim(from: 0, to: clamped)
                        .stroke(ring.color, style: StrokeStyle(lineWidth: lineWidth, lineCap: .round))
                        .rotationEffect(.degrees(-90))
                }
                .padding(inset)
            }
        }
        .frame(width: size, height: size)
    }
}

#Preview {
    HStack(spacing: 24) {
        ActivityRing(value: 0.6, size: 76, lineWidth: 6)
        TripleRing(
            rings: [(0.6, .warning), (0.67, .accent), (0.56, .success)],
            size: 124, lineWidth: 10
        )
    }
    .padding()
    .background(Color.bg)
}
