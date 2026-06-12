//
//  ProgramsRootView.swift
//  GymApp
//
//  Programs entry point (Direction A): the first-run gate. Shows the onboarding
//  (Follow a template vs Build your own) until the user has chosen a setup mode
//  and has at least one program; otherwise the active-program spine
//  (ProgramsHomeView). The host NavigationStack drives routing via the shared
//  programNavigate environment.
//

import SwiftUI

struct ProgramsRootView: View {
    @Environment(SettingsStore.self) private var settings
    @Environment(ProgramsStore.self) private var store
    @Environment(\.programNavigate) private var navigate

    var body: some View {
        @Bindable var settings = settings
        Group {
            if settings.programSetupMode == nil || store.programs.isEmpty {
                ProgramsOnboardingView { mode in
                    settings.programSetupMode = mode
                    switch mode {
                    case .template: navigate(.programTemplates)
                    case .build: navigate(.programEditor)
                    }
                }
            } else {
                ProgramsHomeView()
            }
        }
        .background(Color.bg)
        .navigationTitle("")
        .navigationBarTitleDisplayMode(.inline)
    }
}

#Preview("Onboarding") {
    NavigationStack {
        ProgramsRootView()
            .environment(SettingsStore())
            .environment(ProgramsStore())
            .environment(\.editorialAccent, AccentChoice.clay.color(for: .light))
    }
}

#Preview("Spine") {
    NavigationStack {
        ProgramsRootView()
            .environment(
                {
                    let s = SettingsStore()
                    s.programSetupMode = .template
                    return s
                }()
            )
            .environment(ProgramsStore())
            .environment(\.editorialAccent, AccentChoice.clay.color(for: .light))
    }
}
