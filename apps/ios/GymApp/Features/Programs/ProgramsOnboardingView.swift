//
//  ProgramsOnboardingView.swift
//  GymApp
//
//  First-run programs onboarding (Direction A §2). Shown when
//  settings.programSetupMode == nil (or the library is empty). Two editorial
//  choice cards: Follow a template (primary, ink fill) vs Build your own
//  (outline). Choosing sets the mode and routes the host.
//

import SwiftUI

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

                VStack(spacing: 14) {
                    primaryCard
                    outlineCard
                }
            }
            .padding(.horizontal, 24)
            .padding(.bottom, 32)
            .frame(maxWidth: .infinity, alignment: .leading)
        }
        .background(Color.bg)
        .scrollIndicators(.hidden)
    }

    // MARK: Cards

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
                Text("Compose days, exercises, set/rep schemes and a progression strategy from a blank slate.")
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

#Preview {
    ProgramsOnboardingView { _ in }
        .environment(\.editorialAccent, AccentChoice.clay.color(for: .light))
}
