//
//  Config.swift
//  GymApp
//
//  Network configuration. `baseURL` defaults to the local dev API; the iOS
//  simulator reaches the host loopback at `localhost`. Production base URLs and
//  Apple/Google sign-in are out of scope for this phase.
//

import Foundation

/// Static network configuration. Kept tiny on purpose — a single base URL today;
/// environment switching can layer on later without touching call sites.
enum Config {
    /// API base. The simulator can reach the Mac host on `localhost`. Plain HTTP
    /// is allowed in DEBUG via the `NSAllowsLocalNetworking` ATS exception.
    static let baseURL = URL(string: "http://localhost:8000")!

    /// All routes are mounted under `/v1`.
    static let apiPrefix = "/v1"

    /// Stable dev sign-in subject used by the DEBUG auto-sign-in seam.
    static let devSubject = "ios-dev-user"
    static let devEmail = "ios-dev-user@example.com"
}
