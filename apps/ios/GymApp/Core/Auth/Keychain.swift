//
//  Keychain.swift
//  GymApp
//
//  Minimal generic-password Keychain wrapper for storing the auth tokens.
//  Synchronous and thread-safe (the Security framework is). Keyed by account
//  string within a single service namespace.
//

import Foundation
import Security

/// Tiny `kSecClassGenericPassword` get/set/delete helper. No iCloud sync,
/// device-only, available after first unlock.
struct Keychain: Sendable {
    let service: String

    init(service: String = "com.virajsingh.gymapp.auth") {
        self.service = service
    }

    /// Store (or replace) a UTF-8 string for `account`. Returns false on failure.
    @discardableResult
    func set(_ value: String, for account: String) -> Bool {
        guard let data = value.data(using: .utf8) else { return false }
        var query = baseQuery(account: account)
        SecItemDelete(query as CFDictionary)
        query[kSecValueData as String] = data
        query[kSecAttrAccessible as String] = kSecAttrAccessibleAfterFirstUnlock
        return SecItemAdd(query as CFDictionary, nil) == errSecSuccess
    }

    /// Read the UTF-8 string for `account`, or nil if absent.
    func get(_ account: String) -> String? {
        var query = baseQuery(account: account)
        query[kSecReturnData as String] = true
        query[kSecMatchLimit as String] = kSecMatchLimitOne
        var result: CFTypeRef?
        guard SecItemCopyMatching(query as CFDictionary, &result) == errSecSuccess,
              let data = result as? Data,
              let string = String(data: data, encoding: .utf8)
        else { return nil }
        return string
    }

    /// Remove the entry for `account` (no-op if absent).
    @discardableResult
    func delete(_ account: String) -> Bool {
        let status = SecItemDelete(baseQuery(account: account) as CFDictionary)
        return status == errSecSuccess || status == errSecItemNotFound
    }

    private func baseQuery(account: String) -> [String: Any] {
        [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account,
        ]
    }
}
