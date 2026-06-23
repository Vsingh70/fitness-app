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
    @State private var programsStore: ProgramsStore
    @State private var healthStore: HealthStore
    @State private var todayStore: TodayStore

    init() {
        EditorialAppearance.apply()

        let tokenStore = TokenStore()
        let client = APIClient(tokenStore: tokenStore)
        let auth = AuthService(client: client, tokenStore: tokenStore)
        let programsStore = ProgramsStore(client: client, auth: auth)
        _auth = State(initialValue: auth)
        _programsStore = State(initialValue: programsStore)
        _healthStore = State(initialValue: HealthStore(client: client, auth: auth))
        _todayStore = State(initialValue: TodayStore(client: client, auth: auth, programsStore: programsStore))
    }

    var body: some Scene {
        WindowGroup {
            AppRoot()
                .environment(settings)
                .environment(auth)
                .environment(programsStore)
                .environment(healthStore)
                .environment(todayStore)
                .preferredColorScheme(settings.appearance.colorScheme)
                .task {
                    // DEBUG: dev-sign-in (if needed) then load live data.
                    await auth.ensureSignedIn()
                    await programsStore.load()
                    await healthStore.load()
                    // Today reuses the now-loaded ProgramsStore for the rotation.
                    await todayStore.load()
                }
        }
    }
}
