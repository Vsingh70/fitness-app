//
//  Color+Editorial.swift
//  GymApp
//
//  Semantic colors for the editorial design system. Values live in the asset
//  catalog (light + dark variants) — never hardcode hex in views.
//  See tasks/claude-code-editorial-ios.md §1.
//

import SwiftUI

extension Color {
    /// App background — warm paper (light) / warm near-black (dark).
    static let bg = Color("BG")
    /// Raised paper / grouped row background.
    static let surface = Color("Surface")
    /// Elevated surface (cards, sheets).
    static let surface2 = Color("Surface2")
    /// Primary ink.
    static let ink = Color("Label")
    /// Secondary ink (56%).
    static let ink2 = Color("Label2")
    /// Tertiary ink (32%).
    static let ink3 = Color("Label3")
    /// Hairline rules (14%).
    static let hairline = Color("Separator")
    /// Faint fill (5–6%).
    static let fill = Color("Fill")
    /// The single accent — clay by default. Prefer the runtime accent from the
    /// environment (`\.accentColor` is driven by ``AccentChoice``) in views that
    /// honor the user's accent picker; this asset is the static fallback.
    static let accent = Color("Accent")
    /// Positive / up — sage.
    static let success = Color("Success")
    /// Caution — ochre.
    static let warning = Color("Warning")
    /// Delete / error — oxblood.
    static let destructive = Color("Destructive")
    /// Personal-record highlight — mustard.
    static let pr = Color("PR")
}

// Mirror the tokens onto `ShapeStyle` so the leading-dot shorthand works in
// `foregroundStyle(.ink)`, `fill(.hairline)`, `tint(.accent)`, etc.
extension ShapeStyle where Self == Color {
    static var bg: Color { Color.bg }
    static var surface: Color { Color.surface }
    static var surface2: Color { Color.surface2 }
    static var ink: Color { Color.ink }
    static var ink2: Color { Color.ink2 }
    static var ink3: Color { Color.ink3 }
    static var hairline: Color { Color.hairline }
    static var fill: Color { Color.fill }
    static var accent: Color { Color.accent }
    static var success: Color { Color.success }
    static var warning: Color { Color.warning }
    static var destructive: Color { Color.destructive }
    static var pr: Color { Color.pr }
}
