//
//  GymAppApp.swift
//  GymApp
//

import SwiftUI

@main
struct GymAppApp: App {
    @State private var settings = SettingsStore()

    init() {
        EditorialAppearance.apply()
    }

    var body: some Scene {
        WindowGroup {
            AppRoot()
                .environment(settings)
                .preferredColorScheme(settings.appearance.colorScheme)
        }
    }
}
