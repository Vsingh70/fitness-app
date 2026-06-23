//
//  TokenStore.swift
//  GymApp
//
//  Holds the access + refresh tokens, persisted in the Keychain. Observable so
//  the app shell can react to sign-in/out. The access token is what the
//  `APIClient` reads for the `Authorization: Bearer` header; the refresh token
//  feeds the 401 retry path.
//

import Foundation

@MainActor
@Observable
final class TokenStore {
    /// Current access token (short-lived JWT), or nil when signed out.
    private(set) var accessToken: String?
    /// Current refresh token (opaque), or nil when signed out.
    private(set) var refreshToken: String?

    /// True when an access token is present. Not a validity check — the token
    /// may be expired; the `APIClient` handles 401 refresh.
    var isSignedIn: Bool { accessToken != nil }

    private let keychain: Keychain

    private enum Account {
        static let access = "auth.accessToken"
        static let refresh = "auth.refreshToken"
    }

    init(keychain: Keychain = Keychain()) {
        self.keychain = keychain
        accessToken = keychain.get(Account.access)
        refreshToken = keychain.get(Account.refresh)
    }

    /// Persist a fresh token pair from an auth/refresh response.
    func update(access: String, refresh: String) {
        accessToken = access
        refreshToken = refresh
        keychain.set(access, for: Account.access)
        keychain.set(refresh, for: Account.refresh)
    }

    /// Wipe both tokens from memory and the Keychain.
    func clear() {
        accessToken = nil
        refreshToken = nil
        keychain.delete(Account.access)
        keychain.delete(Account.refresh)
    }
}
