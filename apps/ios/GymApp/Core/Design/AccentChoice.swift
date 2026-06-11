//
//  AccentChoice.swift
//  GymApp
//
//  The user-selectable accent. Defaults to Clay. Swapped live via an
//  environment value so the whole app retints without a relaunch.
//  See tasks/claude-code-editorial-ios.md §1.
//

import SwiftUI

/// The five muted editorial accents the user can pick between.
enum AccentChoice: String, CaseIterable, Identifiable, Sendable {
    case clay, slate, teal, ochre, rose

    var id: String { rawValue }

    var title: String {
        switch self {
        case .clay:  return "Clay"
        case .slate: return "Slate"
        case .teal:  return "Teal"
        case .ochre: return "Ochre"
        case .rose:  return "Rose"
        }
    }

    /// Light-appearance hex (from the editorial guide's muted set).
    private var lightHex: UInt32 {
        switch self {
        case .clay:  return 0x9D5635
        case .slate: return 0x4C4A57
        case .teal:  return 0x4F6B63
        case .ochre: return 0xB07B3C
        case .rose:  return 0x99506A
        }
    }

    /// Dark-appearance hex (lifted ~12% L per the guide).
    private var darkHex: UInt32 {
        switch self {
        case .clay:  return 0xC67E5A
        case .slate: return 0x8E8B9B
        case .teal:  return 0x7FA095
        case .ochre: return 0xC9974F
        case .rose:  return 0xBE8298
        }
    }

    /// Resolves the accent for the given color scheme.
    func color(for scheme: ColorScheme) -> Color {
        Color(hex: scheme == .dark ? darkHex : lightHex)
    }

    /// A scheme-agnostic swatch for the picker dots (uses the light hex).
    var swatch: Color { Color(hex: lightHex) }
}

extension Color {
    /// sRGB color from a 24-bit hex literal. Used only for the runtime accent,
    /// which can't live as a single static asset color; everything else routes
    /// through the asset catalog.
    init(hex: UInt32) {
        self.init(
            .sRGB,
            red:   Double((hex >> 16) & 0xFF) / 255,
            green: Double((hex >> 8) & 0xFF) / 255,
            blue:  Double(hex & 0xFF) / 255,
            opacity: 1
        )
    }
}

// MARK: - Environment

private struct AccentColorKey: EnvironmentKey {
    static let defaultValue: Color = .accent
}

extension EnvironmentValues {
    /// The resolved accent color for the current scheme. Read this in views
    /// instead of `Color.accent` so the accent picker takes effect live.
    var editorialAccent: Color {
        get { self[AccentColorKey.self] }
        set { self[AccentColorKey.self] = newValue }
    }
}
