//
//  MainTabView.swift
//  GymApp
//
//  The 5-tab shell: Today, Workouts, Nutrition, Insights, Settings.
//  See tasks/redesign/claude-code-editorial-ios.md §3 (tab bar) and §4 (screen map).
//

import SwiftUI

struct MainTabView: View {
    @Environment(AppNavigator.self) private var navigator

    var body: some View {
        @Bindable var navigator = navigator
        TabView(selection: $navigator.tab) {
            Tab("Today", systemImage: "calendar", value: AppNavigator.Tab.today) {
                TodayView()
            }
            Tab("Workouts", systemImage: "dumbbell", value: AppNavigator.Tab.workouts) {
                WorkoutsView()
            }
            Tab("Nutrition", systemImage: "fork.knife", value: AppNavigator.Tab.nutrition) {
                NutritionView()
            }
            Tab("Insights", systemImage: "chart.line.uptrend.xyaxis", value: AppNavigator.Tab.insights) {
                InsightsView()
            }
            Tab("Settings", systemImage: "gearshape", value: AppNavigator.Tab.settings) {
                SettingsView()
            }
        }
    }
}
