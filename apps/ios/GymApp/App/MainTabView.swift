//
//  MainTabView.swift
//  GymApp
//
//  The 5-tab shell: Today, Workouts, Nutrition, Insights, Settings.
//  See tasks/redesign/claude-code-editorial-ios.md §3 (tab bar) and §4 (screen map).
//

import SwiftUI

struct MainTabView: View {
    enum TabItem: Hashable { case today, workouts, nutrition, insights, settings }

    @State private var selection: TabItem = .today

    var body: some View {
        TabView(selection: $selection) {
            Tab("Today", systemImage: "calendar", value: TabItem.today) {
                TodayView()
            }
            Tab("Workouts", systemImage: "dumbbell", value: TabItem.workouts) {
                WorkoutsView()
            }
            Tab("Nutrition", systemImage: "fork.knife", value: TabItem.nutrition) {
                NutritionView()
            }
            Tab("Insights", systemImage: "chart.line.uptrend.xyaxis", value: TabItem.insights) {
                InsightsView()
            }
            Tab("Settings", systemImage: "gearshape", value: TabItem.settings) {
                SettingsView()
            }
        }
    }
}
