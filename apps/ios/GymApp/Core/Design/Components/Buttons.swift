//
//  Buttons.swift
//  GymApp
//
//  Primary = ink fill / paper label. Secondary = outline, inverts on press.
//  See tasks/redesign/claude-code-editorial-ios.md §3.
//

import SwiftUI

/// Ink fill, paper label, 7pt radius, 50pt height.
struct PrimaryButtonStyle: ButtonStyle {
    var height: CGFloat = 50
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.system(size: 15, weight: .semibold))
            .frame(maxWidth: .infinity)
            .frame(height: height)
            .background(Color.ink)
            .foregroundStyle(Color.bg)
            .clipShape(RoundedRectangle(cornerRadius: 7))
            .opacity(configuration.isPressed ? 0.85 : 1)
    }
}

/// Transparent, 1pt ink border, ink label — inverts to ink fill on press.
struct SecondaryButtonStyle: ButtonStyle {
    var height: CGFloat = 50
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.system(size: 15, weight: .semibold))
            .frame(maxWidth: .infinity)
            .frame(height: height)
            .background(configuration.isPressed ? Color.ink : .clear)
            .foregroundStyle(configuration.isPressed ? Color.bg : Color.ink)
            .overlay(RoundedRectangle(cornerRadius: 7).stroke(Color.ink, lineWidth: 1))
            .clipShape(RoundedRectangle(cornerRadius: 7))
    }
}

/// Small hairline-bordered button for inline actions ("Apply", "See all").
struct SmallTonalButtonStyle: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.system(size: 13, weight: .semibold))
            .padding(.horizontal, 16)
            .frame(height: 34)
            .overlay(RoundedRectangle(cornerRadius: 7).stroke(Color.ink, lineWidth: 1))
            .foregroundStyle(Color.ink)
            .opacity(configuration.isPressed ? 0.6 : 1)
    }
}

extension ButtonStyle where Self == PrimaryButtonStyle {
    static var editorialPrimary: PrimaryButtonStyle { .init() }
}
extension ButtonStyle where Self == SecondaryButtonStyle {
    static var editorialSecondary: SecondaryButtonStyle { .init() }
}
extension ButtonStyle where Self == SmallTonalButtonStyle {
    static var editorialSmallTonal: SmallTonalButtonStyle { .init() }
}

#Preview {
    VStack(spacing: 16) {
        Button { } label: { Label("Start workout", systemImage: "play.fill") }
            .buttonStyle(.editorialPrimary)
        Button("Reschedule") { }
            .buttonStyle(.editorialSecondary)
        Button("Apply") { }
            .buttonStyle(.editorialSmallTonal)
    }
    .padding()
    .background(Color.bg)
}
