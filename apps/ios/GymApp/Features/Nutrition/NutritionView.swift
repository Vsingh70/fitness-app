//
//  NutritionView.swift
//  GymApp
//
//  Direction A "Log-first" nutrition day screen. First run shows the onboarding
//  (Flexible vs Create a meal plan); thereafter the day screen: calorie masthead,
//  P/C/F strip, hero quick-add, recent-food chips, and meals (flexible "Meal 1…n"
//  with "+ Add meal", or the active plan's slots). No fixed meal presets.
//

import SwiftUI

struct NutritionView: View {
    enum Route: Hashable { case trends, plans }

    @Environment(SettingsStore.self) private var settings
    @Environment(\.editorialAccent) private var accent

    /// Flexible-mode meals (seeded from mock, appendable via "+ Add meal").
    @State private var flexibleMeals: [MockData.Meal] = MockData.meals
    @State private var addTarget: AddTarget? = nil
    @State private var path: [Route] = []

    /// Which meal an add-food action routes into.
    private struct AddTarget: Identifiable {
        let id = UUID()
        let mealName: String
    }

    var body: some View {
        @Bindable var settings = settings

        NavigationStack(path: $path) {
            Group {
                if settings.nutritionMode == nil {
                    NutritionOnboardingView { mode in
                        settings.nutritionMode = mode
                        if mode == .plan { path = [.plans] }
                    }
                } else {
                    dayScreen
                }
            }
            .background(Color.bg)
            .navigationDestination(for: Route.self) { route in
                switch route {
                case .trends: NutritionHistoryView()
                case .plans:  NutritionPlansView()
                }
            }
            .sheet(item: $addTarget) { target in
                AddFoodSheet(mealName: target.mealName)
            }
        }
    }

    // MARK: Day screen

    private var dayScreen: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 24) {
                masthead
                macroStrip
                quickAdd
                recentChips
                meals
            }
            .padding(.horizontal, 20)
            .padding(.top, 8)
            .padding(.bottom, 28)
        }
        .scrollIndicators(.hidden)
        .navigationTitle("")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Button { path = [.trends] } label: {
                    HStack(spacing: 6) {
                        Text("Day")
                            .foregroundStyle(.ink)
                            .overlay(alignment: .bottom) {
                                Rectangle().fill(Color.ink).frame(height: 1.5).offset(y: 4)
                            }
                        Text("Week").foregroundStyle(.ink2)
                    }
                    .font(.system(size: 12, weight: .semibold))
                    .textCase(.uppercase)
                    .tracking(0.96)
                }
            }
        }
    }

    // MARK: 1 · Masthead

    private var masthead: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text(MockData.todayKicker).kicker()
            Text("Today")
                .font(.largeTitleSerif)
                .foregroundStyle(.ink)
            HStack(alignment: .firstTextBaseline, spacing: 12) {
                Text(MockData.kcalConsumed.formatted())
                    .font(.system(size: 52, weight: .medium, design: .serif))
                    .monospacedDigit()
                    .foregroundStyle(.ink)
                Text("/ \(MockData.kcalTarget.formatted()) · \(MockData.kcalRemaining.formatted()) left")
                    .font(.bodyText)
                    .monospacedDigit()
                    .foregroundStyle(.ink2)
            }
        }
    }

    // MARK: 2 · Macro strip (P / C / F)

    private var macroStrip: some View {
        HStack(spacing: 20) {
            ForEach(MockData.macroLines) { line in
                VStack(alignment: .leading, spacing: 0) {
                    Rectangle().fill(Color.hairline).frame(height: 1)
                    Text(line.label).kicker().padding(.top, 10)
                    HStack(alignment: .firstTextBaseline, spacing: 0) {
                        Text("\(line.value)")
                            .font(.figureSmall).monospacedDigit().foregroundStyle(.ink)
                        Text("/\(line.target)g")
                            .font(.footnote).monospacedDigit().foregroundStyle(.ink2)
                    }
                    .padding(.top, 6)
                }
                .frame(maxWidth: .infinity, alignment: .leading)
            }
        }
    }

    // MARK: 3 · Quick-add (hero)

    private var quickAdd: some View {
        Button { addTarget = AddTarget(mealName: defaultAddMealName) } label: {
            HStack(spacing: 12) {
                Text("What did you eat?")
                    .font(.system(size: 17, design: .serif))
                    .foregroundStyle(.ink2)
                Spacer(minLength: 8)
                Image(systemName: "plus")
                    .font(.system(size: 18, weight: .semibold))
                    .foregroundStyle(Color.bg)
                    .frame(width: 36, height: 36)
                    .background(accent)
                    .clipShape(RoundedRectangle(cornerRadius: 6))
            }
            .padding(.leading, 16)
            .padding(.trailing, 8)
            .frame(height: 52)
            .overlay(RoundedRectangle(cornerRadius: 8).stroke(Color.ink, lineWidth: 1.5))
        }
        .buttonStyle(.plain)
    }

    // MARK: 4 · Recent chips

    private var recentChips: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("Recent & frequent").kicker()
            ScrollView(.horizontal) {
                HStack(spacing: 8) {
                    ForEach(MockData.recentFoods) { food in
                        Button { addTarget = AddTarget(mealName: defaultAddMealName) } label: {
                            HStack(spacing: 8) {
                                Text(food.name)
                                    .font(.footnote).foregroundStyle(.ink)
                                Text("\(food.kcalPer100)")
                                    .font(.figureSmall).monospacedDigit().foregroundStyle(.ink)
                                Image(systemName: "plus")
                                    .font(.system(size: 11, weight: .semibold))
                                    .foregroundStyle(.ink2)
                            }
                            .padding(.horizontal, 14).padding(.vertical, 9)
                            .overlay(Capsule().stroke(Color.hairline, lineWidth: 1))
                        }
                        .buttonStyle(.plain)
                    }
                }
                .padding(.horizontal, 1)
            }
            .scrollIndicators(.hidden)
        }
    }

    // MARK: 5 · Meals

    @ViewBuilder
    private var meals: some View {
        if settings.nutritionMode == .plan {
            planMeals
        } else {
            flexibleMealsList
        }
    }

    private var flexibleMealsList: some View {
        VStack(alignment: .leading, spacing: 0) {
            Text("Meals").kicker().padding(.bottom, 6)
            ForEach(Array(flexibleMeals.enumerated()), id: \.element.id) { index, meal in
                mealRow(name: meal.name ?? "Meal \(index + 1)", meal: meal)
            }
            Button { appendFlexibleMeal() } label: {
                Label("Add meal", systemImage: "plus")
                    .font(.system(size: 14, weight: .semibold))
                    .foregroundStyle(.ink2)
                    .frame(maxWidth: .infinity)
                    .frame(height: 46)
                    .overlay(
                        RoundedRectangle(cornerRadius: 8)
                            .stroke(style: StrokeStyle(lineWidth: 1, dash: [5, 4]))
                            .foregroundStyle(Color.hairline)
                    )
            }
            .buttonStyle(.plain)
            .padding(.top, 12)
        }
    }

    private var planMeals: some View {
        VStack(alignment: .leading, spacing: 0) {
            Text("Plan · \(MockData.activePlan?.name ?? "Today")").kicker().padding(.bottom, 6)
            ForEach(Array((MockData.activePlan?.slots ?? []).enumerated()), id: \.element.id) { _, slot in
                if let meal = slotMeal(for: slot.name) {
                    mealRow(name: slot.name, meal: meal)
                } else {
                    emptySlotRow(slot)
                }
            }
        }
    }

    // MARK: Meal rows

    private func mealRow(name: String, meal: MockData.Meal) -> some View {
        VStack(spacing: 0) {
            Rectangle().fill(Color.hairline).frame(height: 1)
            HStack(alignment: .top, spacing: 12) {
                VStack(alignment: .leading, spacing: 3) {
                    HStack(spacing: 8) {
                        Text(name).font(.figureSmall).foregroundStyle(.ink)
                        Text(meal.at).font(.caption2).foregroundStyle(.ink3)
                            .textCase(.uppercase).tracking(0.8)
                    }
                    if meal.items.isEmpty {
                        Button { addTarget = AddTarget(mealName: name) } label: {
                            Label("Add food", systemImage: "plus")
                                .font(.footnote).foregroundStyle(accent)
                        }
                        .buttonStyle(.plain)
                    } else {
                        Text(meal.items.map(\.name).joined(separator: ", "))
                            .font(.footnote).foregroundStyle(.ink2)
                            .fixedSize(horizontal: false, vertical: true)
                    }
                }
                Spacer(minLength: 8)
                if !meal.items.isEmpty {
                    VStack(alignment: .trailing, spacing: 2) {
                        Text("\(meal.kcal)")
                            .font(.figureSmall).monospacedDigit().foregroundStyle(.ink)
                        Text("\(meal.protein)g P")
                            .font(.caption2).monospacedDigit().foregroundStyle(accent)
                    }
                }
            }
            .padding(.vertical, 14)
        }
    }

    private func emptySlotRow(_ slot: MockData.NutritionMealSlot) -> some View {
        VStack(spacing: 0) {
            Rectangle().fill(Color.hairline).frame(height: 1)
            HStack(alignment: .center, spacing: 12) {
                VStack(alignment: .leading, spacing: 3) {
                    Text(slot.name).font(.figureSmall).foregroundStyle(.ink)
                    Button { addTarget = AddTarget(mealName: slot.name) } label: {
                        Label("Add food", systemImage: "plus")
                            .font(.footnote).foregroundStyle(accent)
                    }
                    .buttonStyle(.plain)
                }
                Spacer(minLength: 8)
                if let kcal = slot.kcal {
                    Text("\(kcal)")
                        .font(.figureSmall).monospacedDigit().foregroundStyle(.ink3)
                }
            }
            .padding(.vertical, 14)
        }
    }

    // MARK: Helpers

    /// Quick-add and recent chips drop into the first meal with room, or a fresh one.
    private var defaultAddMealName: String {
        if settings.nutritionMode == .plan {
            return MockData.activePlan?.slots.first?.name ?? "Meal 1"
        }
        return flexibleMeals.first?.name ?? "Meal 1"
    }

    private func slotMeal(for name: String) -> MockData.Meal? {
        MockData.meals.first { ($0.name ?? "").caseInsensitiveCompare(name) == .orderedSame && !$0.items.isEmpty }
    }

    private func appendFlexibleMeal() {
        flexibleMeals.append(
            MockData.Meal(at: "—", kcal: 0, protein: 0, carbs: 0, fat: 0, items: [])
        )
    }
}

#Preview("Day") {
    NutritionView()
        .environment({ let s = SettingsStore(); s.nutritionMode = .flexible; return s }())
        .environment(\.editorialAccent, AccentChoice.clay.color(for: .light))
}

#Preview("Onboarding") {
    NutritionView()
        .environment(SettingsStore())
        .environment(\.editorialAccent, AccentChoice.clay.color(for: .light))
}
