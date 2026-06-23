//
//  GymAppApp.swift
//  GymApp
//

import SwiftUI

@main
struct GymAppApp: App {
    @State private var settings = SettingsStore()

    // Networking + auth + data stack, built once and shared via the environment.
    @State private var auth: AuthService
    @State private var navigator = AppNavigator()
    @State private var programsStore: ProgramsStore
    @State private var workoutsStore: WorkoutsStore
    @State private var healthStore: HealthStore
    @State private var todayStore: TodayStore
    @State private var nutritionStore: NutritionStore
    @State private var insightsStore: InsightsStore

    init() {
        EditorialAppearance.apply()

        let tokenStore = TokenStore()
        let client = APIClient(tokenStore: tokenStore)
        let auth = AuthService(client: client, tokenStore: tokenStore)
        let programsStore = ProgramsStore(client: client, auth: auth)
        _auth = State(initialValue: auth)
        _programsStore = State(initialValue: programsStore)
        _workoutsStore = State(initialValue: WorkoutsStore(client: client, auth: auth, programsStore: programsStore))
        _healthStore = State(initialValue: HealthStore(client: client, auth: auth))
        _todayStore = State(initialValue: TodayStore(client: client, auth: auth, programsStore: programsStore))
        _nutritionStore = State(initialValue: NutritionStore(client: client, auth: auth))
        _insightsStore = State(initialValue: InsightsStore(client: client, auth: auth))
    }

    var body: some Scene {
        WindowGroup {
            AppRoot()
                .environment(settings)
                .environment(auth)
                .environment(navigator)
                .environment(programsStore)
                .environment(workoutsStore)
                .environment(healthStore)
                .environment(todayStore)
                .environment(nutritionStore)
                .environment(insightsStore)
                .preferredColorScheme(settings.appearance.colorScheme)
                .task {
                    // DEBUG: dev-sign-in (if needed) then load live data.
                    await auth.ensureSignedIn()
                    await programsStore.load()
                    await workoutsStore.loadHistory()
                    await healthStore.load()
                    // Today reuses the now-loaded ProgramsStore for the rotation.
                    await todayStore.load()
                    await nutritionStore.load()
                    await insightsStore.load()
                }
        }
    }
}
