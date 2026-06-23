//
//  ProgramsOnboardingView.swift
//  GymApp
//
//  The two-card create chooser (Direction A §2): Follow a template (primary, ink
//  fill) vs Build your own (outline). This is the single entry for *every*
//  create, not first-run only:
//  - `ProgramsOnboardingView` is the first-run screen (zero programs / no mode).
//  - `ProgramChooserView` is the same chooser reached from every "New program" /
//    "Create a new program" action once the user already has programs.
//  Both render the shared `ProgramChooserCards`.
//

import SwiftUI

// MARK: First-run onboarding (whole screen)

struct ProgramsOnboardingView: View {
    @Environment(\.editorialAccent) private var accent

    /// Called with the chosen mode; the host persists it + routes.
    let onChoose: (ProgramSetupMode) -> Void

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 0) {
                VStack(alignment: .leading, spacing: 12) {
                    Text("Welcome to programs").kicker()
                    Text("How do you want to train?")
                        .font(.largeTitleSerif)
                        .foregroundStyle(.ink)
                        .fixedSize(horizontal: false, vertical: true)
                    Text("First time here — start from a proven template, or build your own. You can switch anytime.")
                        .font(.bodyText)
                        .foregroundStyle(.ink2)
                        .fixedSize(horizontal: false, vertical: true)
                }
                .padding(.top, 36)
                .padding(.bottom, 28)

                ProgramChooserCards(onChoose: onChoose)
            }
            .padding(.horizontal, 24)
            .padding(.bottom, 32)
            .frame(maxWidth: .infinity, alignment: .leading)
        }
        .background(Color.bg)
        .scrollIndicators(.hidden)
    }
}

// MARK: Every-create chooser (pushed screen)

/// The "New program" chooser. Reached from every create affordance once the user
/// already has programs — so a template is always an option, not only a blank
/// build. Routes the host to Browse templates or the blank builder.
struct ProgramChooserView: View {
    @Environment(SettingsStore.self) private var settings
    @Environment(\.programNavigate) private var navigate

    var body: some View {
        @Bindable var settings = settings
        ScrollView {
            VStack(alignment: .leading, spacing: 0) {
                VStack(alignment: .leading, spacing: 12) {
                    Text("New program").kicker()
                    Text("Start a new program")
                        .font(.largeTitleSerif)
                        .foregroundStyle(.ink)
                        .fixedSize(horizontal: false, vertical: true)
                    Text("Copy a proven template or build one from scratch. Either way it lands inactive — activate it when you're ready.")
                        .font(.bodyText)
                        .foregroundStyle(.ink2)
                        .fixedSize(horizontal: false, vertical: true)
                }
                .padding(.top, 18)
                .padding(.bottom, 28)

                ProgramChooserCards { mode in
                    settings.programSetupMode = mode
                    switch mode {
                    case .template: navigate(.programTemplates)
                    case .build:    navigate(.programEditor)
                    }
                }
            }
            .padding(.horizontal, 24)
            .padding(.bottom, 32)
            .frame(maxWidth: .infinity, alignment: .leading)
        }
        .background(Color.bg)
        .scrollIndicators(.hidden)
        .navigationTitle("")
        .navigationBarTitleDisplayMode(.inline)
    }
}

// MARK: Shared cards

/// The two editorial choice cards. Used by both the first-run onboarding and the
/// every-create chooser so they stay in lockstep.
struct ProgramChooserCards: View {
    @Environment(\.editorialAccent) private var accent
    let onChoose: (ProgramSetupMode) -> Void

    var body: some View {
        VStack(spacing: 14) {
            primaryCard
            outlineCard
        }
    }

    private var primaryCard: some View {
        Button { onChoose(.template) } label: {
            VStack(alignment: .leading, spacing: 10) {
                Text("Recommended")
                    .font(.system(size: 11, weight: .semibold))
                    .textCase(.uppercase)
                    .tracking(1.6)
                    .foregroundStyle(Color.bg.opacity(0.7))
                Text("Follow a template")
                    .font(.title2Serif)
                    .foregroundStyle(Color.bg)
                Text("Pick a proven program — PPL, Upper/Lower, 5/3/1 and more. Copy it, tweak if you like, and start this week.")
                    .font(.footnote)
                    .foregroundStyle(Color.bg.opacity(0.8))
                    .fixedSize(horizontal: false, vertical: true)
                cta("Browse templates →", color: Color.bg)
                    .padding(.top, 4)
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(22)
            .background(Color.ink)
            .clipShape(RoundedRectangle(cornerRadius: 6))
        }
        .buttonStyle(.plain)
    }

    private var outlineCard: some View {
        Button { onChoose(.build) } label: {
            VStack(alignment: .leading, spacing: 10) {
                Text("Full control").kicker()
                Text("Build your own program")
                    .font(.title2Serif)
                    .foregroundStyle(.ink)
                Text("Compose slots, exercises, set/rep schemes and a progression strategy from a blank slate.")
                    .font(.footnote)
                    .foregroundStyle(.ink2)
                    .fixedSize(horizontal: false, vertical: true)
                cta("Start building →", color: accent)
                    .padding(.top, 4)
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(22)
            .overlay(RoundedRectangle(cornerRadius: 6).stroke(Color.hairline, lineWidth: 1))
        }
        .buttonStyle(.plain)
    }

    private func cta(_ text: String, color: Color) -> some View {
        Text(text)
            .font(.system(size: 12, weight: .semibold))
            .textCase(.uppercase)
            .tracking(1.2)
            .foregroundStyle(color)
    }
}

#Preview("First run") {
    ProgramsOnboardingView { _ in }
        .environment(\.editorialAccent, AccentChoice.clay.color(for: .light))
}

#Preview("Chooser") {
    NavigationStack {
        ProgramChooserView()
            .environment(SettingsStore())
            .environment(\.editorialAccent, AccentChoice.clay.color(for: .light))
    }
}
