//
//  Typography.swift
//  GymApp
//
//  Editorial type ramp: New York (.serif) for titles & figures, SF (.default)
//  for body/UI. Every numeric uses .monospacedDigit().
//  See tasks/claude-code-editorial-ios.md §2.
//

import SwiftUI

extension Font {
    // Display serif — titles & figures. Never exceed .medium weight.
    static let largeTitleSerif = Font.system(size: 34, weight: .medium, design: .serif)
    static let titleSerif      = Font.system(size: 24, weight: .medium, design: .serif)
    static let title2Serif     = Font.system(size: 20, weight: .medium, design: .serif)
    /// Stat numbers.
    static let figure          = Font.system(size: 30, weight: .medium, design: .serif)
    static let figureSmall     = Font.system(size: 18, weight: .medium, design: .serif)

    // Body / UI — sans.
    static let headline        = Font.system(size: 16, weight: .semibold)
    static let bodyText        = Font.system(size: 16)
    static let footnote        = Font.system(size: 13)
    static let caption         = Font.system(size: 12)
    static let caption2        = Font.system(size: 11)
}

/// Uppercase, letter-spaced, secondary — section labels & metadata throughout.
struct Kicker: ViewModifier {
    func body(content: Content) -> some View {
        content
            .font(.system(size: 11, weight: .semibold))
            .textCase(.uppercase)
            .tracking(1.6)
            .foregroundStyle(Color.ink2)
    }
}

extension View {
    /// Applies the editorial kicker treatment (uppercase, tracked, secondary).
    func kicker() -> some View { modifier(Kicker()) }
}
