//
//  AppRoot.swift
//  GymApp
//
//  Root view. (Auth gating is out of scope for the visual pass — this is the
//  signed-in shell.) Resolves the runtime accent into the environment so the
//  whole tree retints when the user changes the accent or the scheme flips.
//

import SwiftUI

struct AppRoot: View {
    @Environment(SettingsStore.self) private var settings
    @Environment(\.colorScheme) private var scheme

    var body: some View {
        MainTabView()
            .tint(.ink) // selected tab tint = ink, not accent
            .environment(\.editorialAccent, settings.accent.color(for: scheme))
    }
}
