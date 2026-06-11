//
//  NutritionOnboardingView.swift
//  GymApp
//
//  First-run nutrition onboarding (Direction A §2). Shown when
//  settings.nutritionMode == nil. Two editorial choice cards: Flexible tracking
//  (primary, ink fill) vs Create a meal plan (outline). Choosing sets the mode.
//

import SwiftUI

struct NutritionOnboardingView: View {
    @Environment(\.editorialAccent) private var accent

    /// Called with the chosen mode; the host persists it + routes.
    let onChoose: (NutritionMode) -> Void

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 0) {
                VStack(alignment: .leading, spacing: 12) {
                    Text("Welcome to nutrition").kicker()
                    Text("How do you want to track?")
                        .font(.largeTitleSerif)
                        .foregroundStyle(.ink)
                        .fixedSize(horizontal: false, vertical: true)
                    Text("First time here — pick a way to get started. You can switch anytime in settings.")
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
        Button { onChoose(.flexible) } label: {
            VStack(alignment: .leading, spacing: 10) {
                Text("Recommended")
                    .font(.system(size: 11, weight: .semibold))
                    .textCase(.uppercase)
                    .tracking(1.6)
                    .foregroundStyle(Color.bg.opacity(0.7))
                Text("Flexible tracking")
                    .font(.title2Serif)
                    .foregroundStyle(Color.bg)
                Text("Log meals freely as you eat — search or scan a barcode. Add as many meals a day as you like. No setup.")
                    .font(.footnote)
                    .foregroundStyle(Color.bg.opacity(0.8))
                    .fixedSize(horizontal: false, vertical: true)
                cta("Start tracking →", color: Color.bg)
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
        Button { onChoose(.plan) } label: {
            VStack(alignment: .leading, spacing: 10) {
                Text("Structured").kicker()
                Text("Create a meal plan")
                    .font(.title2Serif)
                    .foregroundStyle(.ink)
                Text("Build a daily template with a set number of meals and macro targets, then log against it each day.")
                    .font(.footnote)
                    .foregroundStyle(.ink2)
                    .fixedSize(horizontal: false, vertical: true)
                cta("Build a plan →", color: accent)
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
    NutritionOnboardingView { _ in }
        .environment(\.editorialAccent, AccentChoice.clay.color(for: .light))
}
