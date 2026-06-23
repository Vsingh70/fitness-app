//
//  APIClient.swift
//  GymApp
//
//  Async/await JSON client for the v1 API. Reads the bearer token from
//  `TokenStore`, decodes with `.convertFromSnakeCase`, and surfaces a typed
//  `APIError`. On a 401 it attempts a single refresh (wired by `AuthService`
//  via `refreshHandler`) and replays the request once.
//

import Foundation

/// HTTP methods we issue. Bodies are JSON-encoded `Encodable` values.
enum HTTPMethod: String, Sendable {
    case get = "GET"
    case post = "POST"
    case patch = "PATCH"
    case delete = "DELETE"
}

/// Typed failures from the client. `server` carries the API error envelope's
/// code/message when present; otherwise the raw status.
enum APIError: Error, Sendable {
    case invalidURL
    case network(any Error)
    case decoding(any Error)
    case unauthorized
    /// status >= 400 with a parsed (or best-effort) server message.
    case server(status: Int, code: String?, message: String?)

    var isUnauthorized: Bool {
        if case .unauthorized = self { return true }
        if case .server(401, _, _) = self { return true }
        return false
    }
}

@MainActor
final class APIClient {
    private let tokenStore: TokenStore
    private let session: URLSession
    private let decoder: JSONDecoder
    private let encoder: JSONEncoder

    /// Refresh seam. `AuthService` installs this; it should obtain a new token
    /// pair, store it, and return true on success. Kept as a closure to avoid a
    /// retain cycle / init ordering dependency with `AuthService`.
    var refreshHandler: (@MainActor () async -> Bool)?

    init(tokenStore: TokenStore, session: URLSession = .shared) {
        self.tokenStore = tokenStore
        self.session = session

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        self.decoder = decoder

        let encoder = JSONEncoder()
        encoder.keyEncodingStrategy = .convertToSnakeCase
        self.encoder = encoder
    }

    // MARK: - Requests

    /// Decode a JSON response into `T`.
    func request<T: Decodable>(
        _ method: HTTPMethod,
        _ path: String,
        body: (some Encodable)? = Optional<Empty>.none,
        auth: Bool = true
    ) async throws -> T {
        let data = try await requestData(method, path, body: body, auth: auth)
        do {
            return try decoder.decode(T.self, from: data)
        } catch {
            throw APIError.decoding(error)
        }
    }

    /// Fire a request that returns no decodable body (e.g. 204 / activate).
    func requestVoid(
        _ method: HTTPMethod,
        _ path: String,
        body: (some Encodable)? = Optional<Empty>.none,
        auth: Bool = true
    ) async throws {
        _ = try await requestData(method, path, body: body, auth: auth)
    }

    // MARK: - Core

    private func requestData(
        _ method: HTTPMethod,
        _ path: String,
        body: (some Encodable)?,
        auth: Bool,
        isRetry: Bool = false
    ) async throws -> Data {
        let request = try makeRequest(method, path, body: body, auth: auth)

        let data: Data
        let response: URLResponse
        do {
            (data, response) = try await session.data(for: request)
        } catch {
            throw APIError.network(error)
        }

        guard let http = response as? HTTPURLResponse else {
            throw APIError.server(status: -1, code: nil, message: "No HTTP response")
        }

        if http.statusCode == 401, auth, !isRetry, let refresh = refreshHandler {
            if await refresh() {
                return try await requestData(method, path, body: body, auth: auth, isRetry: true)
            }
            throw APIError.unauthorized
        }

        guard (200..<300).contains(http.statusCode) else {
            let envelope = try? decoder.decode(APIErrorEnvelope.self, from: data)
            throw APIError.server(
                status: http.statusCode,
                code: envelope?.error.code,
                message: envelope?.error.message
            )
        }

        return data
    }

    private func makeRequest(
        _ method: HTTPMethod,
        _ path: String,
        body: (some Encodable)?,
        auth: Bool
    ) throws -> URLRequest {
        let fullPath = path.hasPrefix("/v1") ? path : Config.apiPrefix + path
        guard let url = URL(string: fullPath, relativeTo: Config.baseURL) else {
            throw APIError.invalidURL
        }
        var request = URLRequest(url: url)
        request.httpMethod = method.rawValue
        request.setValue("application/json", forHTTPHeaderField: "Accept")

        if let body {
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
            do {
                request.httpBody = try encoder.encode(body)
            } catch {
                throw APIError.decoding(error)
            }
        }

        if auth, let token = tokenStore.accessToken {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        return request
    }
}

/// Placeholder for "no request body" so callers can omit `body:`.
struct Empty: Encodable, Sendable {}
