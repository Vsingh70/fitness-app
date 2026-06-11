//
//  SettingsStore.swift
//  GymApp
//
//  App-wide user preferences (accent, appearance, units). For the visual pass
//  these persist to UserDefaults; networking/sync is out of scope.
//

import SwiftUI

enum AppearanceMode: String, CaseIterable, Identifiable, Sendable {
    case light, auto, dark
    var id: String { rawValue }
    var title: String {
        switch self {
        case .light: return "Light"
        case .auto:  return "Auto"
        case .dark:  return "Dark"
        }
    }
    /// nil = follow the system.
    var colorScheme: ColorScheme? {
        switch self {
        case .light: return .light
        case .auto:  return nil
        case .dark:  return .dark
        }
    }
}

enum WeightUnit: String, CaseIterable, Identifiable, Sendable {
    case kg, lb
    var id: String { rawValue }
    var title: String { rawValue }
}

enum DistanceUnit: String, CaseIterable, Identifiable, Sendable {
    case km, mi
    var id: String { rawValue }
    var title: String { rawValue }
}

/// How the user tracks nutrition. `nil` (unset) → first-run onboarding.
enum NutritionMode: String, CaseIterable, Identifiable, Sendable {
    case flexible, plan
    var id: String { rawValue }
    var title: String {
        switch self {
        case .flexible: return "Flexible"
        case .plan:     return "Plan"
        }
    }
}

@MainActor
@Observable
final class SettingsStore {
    var accent: AccentChoice {
        didSet { defaults.set(accent.rawValue, forKey: Keys.accent) }
    }
    var appearance: AppearanceMode {
        didSet { defaults.set(appearance.rawValue, forKey: Keys.appearance) }
    }
    var weightUnit: WeightUnit {
        didSet { defaults.set(weightUnit.rawValue, forKey: Keys.weightUnit) }
    }
    var distanceUnit: DistanceUnit {
        didSet { defaults.set(distanceUnit.rawValue, forKey: Keys.distanceUnit) }
    }
    /// nil = unset → show the nutrition first-run onboarding.
    var nutritionMode: NutritionMode? {
        didSet { defaults.set(nutritionMode?.rawValue, forKey: Keys.nutritionMode) }
    }

    private let defaults: UserDefaults

    private enum Keys {
        static let accent = "settings.accent"
        static let appearance = "settings.appearance"
        static let weightUnit = "settings.weightUnit"
        static let distanceUnit = "settings.distanceUnit"
        static let nutritionMode = "settings.nutritionMode"
    }

    init(defaults: UserDefaults = .standard) {
        self.defaults = defaults
        accent = defaults.string(forKey: Keys.accent)
            .flatMap(AccentChoice.init) ?? .clay
        appearance = defaults.string(forKey: Keys.appearance)
            .flatMap(AppearanceMode.init) ?? .auto
        weightUnit = defaults.string(forKey: Keys.weightUnit)
            .flatMap(WeightUnit.init) ?? .kg
        distanceUnit = defaults.string(forKey: Keys.distanceUnit)
            .flatMap(DistanceUnit.init) ?? .km
        nutritionMode = defaults.string(forKey: Keys.nutritionMode)
            .flatMap(NutritionMode.init)
    }
}
