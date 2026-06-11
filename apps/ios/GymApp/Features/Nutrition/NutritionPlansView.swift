//
//  NutritionPlansView.swift
//  GymApp
//
//  List + activate nutrition plans. Designed to the editorial system + 08.05
//  spec (no prototype frame).
//

import SwiftUI

struct NutritionPlansView: View {
    @Environment(\.editorialAccent) private var accent

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 12) {
                ForEach(MockData.nutritionPlans) { plan in
                    planCard(plan)
                }
            }
            .padding(.horizontal, 20)
            .padding(.top, 12)
            .padding(.bottom, 24)
        }
        .background(Color.bg)
        .scrollIndicators(.hidden)
        .navigationTitle("Plans")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Button { } label: { Image(systemName: "plus") }
            }
        }
    }

    private func planCard(_ plan: MockData.NutritionPlan) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Text(plan.name).font(.titleSerif).foregroundStyle(.ink)
                if plan.active { EditorialChip(text: "Active", tone: accent) }
                Spacer()
                if !plan.active {
                    Button("Activate") { }.buttonStyle(.editorialSmallTonal)
                }
            }
            HStack(spacing: 0) {
                macroPair("\(plan.kcal)", "kcal")
                Spacer()
                macroPair("\(plan.protein)g", "protein")
                Spacer()
                macroPair("\(plan.carbs)g", "carbs")
                Spacer()
                macroPair("\(plan.fat)g", "fat")
            }
        }
        .padding(16)
        .overlay(
            RoundedRectangle(cornerRadius: 4)
                .stroke(plan.active ? accent.opacity(0.5) : Color.hairline, lineWidth: 1)
        )
    }

    private func macroPair(_ value: String, _ label: String) -> some View {
        VStack(alignment: .leading, spacing: 2) {
            Text(value).font(.figureSmall).monospacedDigit().foregroundStyle(.ink)
            Text(label).font(.caption2).foregroundStyle(.ink2)
        }
    }
}

#Preview {
    NavigationStack {
        NutritionPlansView().environment(\.editorialAccent, AccentChoice.clay.color(for: .light))
    }
}
