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
            switch store.loadState {
            case .loading where store.programs.isEmpty:
                ProgramsLoadingView()
            case .failed(let message) where store.programs.isEmpty:
                ProgramsErrorView(message: message) {
                    Task { await store.load() }
                }
            default:
                if settings.programSetupMode == nil || (store.hasResolved && store.programs.isEmpty) {
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
        }
        .background(Color.bg)
        .navigationTitle("")
        .navigationBarTitleDisplayMode(.inline)
    }
}

// MARK: - Quiet loading / inline error (editorial, Core/Design tokens)

/// A hairline-quiet loading state for the programs spine — a centered spinner
/// over a short kicker. Used while the first live load is in flight.
struct ProgramsLoadingView: View {
    var body: some View {
        VStack(spacing: 14) {
            ProgressView()
                .controlSize(.large)
                .tint(.ink3)
            Text("Loading programs")
                .font(.system(size: 11, weight: .semibold))
                .textCase(.uppercase).tracking(1.2)
                .foregroundStyle(.ink3)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .padding(40)
    }
}

/// Inline error with a single Retry — never a crash, never a blank screen.
struct ProgramsErrorView: View {
    @Environment(\.editorialAccent) private var accent
    let message: String
    let retry: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            Text("Couldn’t load programs").kicker()
            Text(message)
                .font(.system(size: 16, design: .serif))
                .foregroundStyle(.ink2)
                .fixedSize(horizontal: false, vertical: true)
            Button(action: retry) {
                Label("Try again", systemImage: "arrow.clockwise")
            }
            .buttonStyle(.editorialSecondary)
            .padding(.top, 4)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(28)
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
