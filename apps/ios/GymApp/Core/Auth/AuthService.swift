//
//  AuthService.swift
//  GymApp
//
//  Owns the auth lifecycle for this phase: DEBUG dev sign-in against
//  `POST /v1/auth/dev`, token persistence via `TokenStore`, and the refresh
//  path (`POST /v1/auth/refresh`) used by `APIClient`'s 401 retry.
//
//  Production Apple/Google sign-in is intentionally out of scope — the
//  `exchange` seam lives at `POST /v1/auth/exchange` for a later feature.
//

import Foundation

@MainActor
@Observable
final class AuthService {
    private let client: APIClient
    private let tokenStore: TokenStore

    /// Whether a token is currently stored. Mirrors `TokenStore.isSignedIn`.
    var isSignedIn: Bool { tokenStore.isSignedIn }

    init(client: APIClient, tokenStore: TokenStore) {
        self.client = client
        self.tokenStore = tokenStore
        // Wire the 401 refresh seam. DEBUG falls back to dev sign-in if refresh
        // fails or there is no refresh token.
        client.refreshHandler = { [weak self] in
            await self?.refresh() ?? false
        }
    }

    // MARK: - Dev sign-in (DEBUG seam)

    /// Sign in via the dev-only endpoint and persist the token pair.
    func devSignIn(
        sub: String = Config.devSubject,
        email: String = Config.devEmail
    ) async throws {
        struct DevRequest: Encodable { let sub: String; let email: String }
        let pair: APITokenPair = try await client.request(
            .post, "/auth/dev",
            body: DevRequest(sub: sub, email: email),
            auth: false
        )
        tokenStore.update(access: pair.accessToken, refresh: pair.refreshToken)
    }

    /// In DEBUG, ensure there is a usable token: dev-sign-in if none stored.
    /// No-op in release builds (production sign-in is a separate feature).
    func ensureSignedIn() async {
        #if DEBUG
        guard !tokenStore.isSignedIn else { return }
        do {
            try await devSignIn()
        } catch {
            // Leave signed-out; the store surfaces the error on first load.
        }
        #endif
    }

    // MARK: - Refresh

    /// Rotate tokens via `POST /v1/auth/refresh`. Returns true on success.
    /// In DEBUG, falls back to a fresh dev sign-in when refresh is unavailable.
    @discardableResult
    func refresh() async -> Bool {
        if let token = tokenStore.refreshToken {
            struct RefreshRequest: Encodable { let refreshToken: String }
            do {
                let pair: APITokenPair = try await client.request(
                    .post, "/auth/refresh",
                    body: RefreshRequest(refreshToken: token),
                    auth: false
                )
                tokenStore.update(access: pair.accessToken, refresh: pair.refreshToken)
                return true
            } catch {
                // fall through to the DEBUG dev-sign-in fallback
            }
        }
        #if DEBUG
        do {
            try await devSignIn()
            return true
        } catch {
            return false
        }
        #else
        return false
        #endif
    }

    /// Sign out: clear stored tokens.
    func signOut() {
        tokenStore.clear()
    }
}
