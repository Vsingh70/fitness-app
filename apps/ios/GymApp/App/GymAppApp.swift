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

    init() {
        EditorialAppearance.apply()

        let tokenStore = TokenStore()
        let client = APIClient(tokenStore: tokenStore)
        let auth = AuthService(client: client, tokenStore: tokenStore)
        _auth = State(initialValue: auth)
        _programsStore = State(initialValue: ProgramsStore(client: client, auth: auth))
        _healthStore = State(initialValue: HealthStore(client: client, auth: auth))
    }

    var body: some Scene {
        WindowGroup {
            AppRoot()
                .environment(settings)
                .environment(auth)
                .environment(programsStore)
                .environment(healthStore)
                .preferredColorScheme(settings.appearance.colorScheme)
                .task {
                    // DEBUG: dev-sign-in (if needed) then load live data.
                    await auth.ensureSignedIn()
                    await programsStore.load()
                    await healthStore.load()
                }
        }
    }
}
