//
//  RestBar.swift
//  GymApp
//
//  Floating rest-timer bar — the ONE place a shadow is allowed. Material blur,
//  hairline border, 14pt radius. See §3 (active workout) and §0.
//

import SwiftUI

struct RestBar: View {
    let elapsed: String
    let total: String
    let fraction: Double
    var onAddTime: () -> Void = {}
    var onSkip: () -> Void = {}

    var body: some View {
        HStack(spacing: 12) {
            ZStack {
                ActivityRing(value: fraction, size: 44, lineWidth: 4)
                Text(elapsed)
                    .font(.system(size: 14, weight: .bold))
                    .monospacedDigit()
                    .foregroundStyle(.ink)
            }
            VStack(alignment: .leading, spacing: 1) {
                Text("Resting").font(.system(size: 14, weight: .semibold)).foregroundStyle(.ink)
                Text("\(elapsed) of \(total) · auto-started")
                    .font(.caption).foregroundStyle(.ink2)
            }
            Spacer(minLength: 8)
            HStack(spacing: 6) {
                Button("+30s", action: onAddTime)
                    .buttonStyle(.editorialSmallTonal)
                Button("Skip", action: onSkip)
                    .buttonStyle(.editorialSmallTonal)
            }
        }
        .padding(.horizontal, 14)
        .padding(.vertical, 10)
        .background(.thinMaterial, in: RoundedRectangle(cornerRadius: 14))
        .overlay(RoundedRectangle(cornerRadius: 14).stroke(Color.hairline, lineWidth: 1))
        .shadow(color: .black.opacity(0.10), radius: 10, x: 0, y: 6)
    }
}
