//
//  WearableConnectionCard.swift
//  GymApp
//
//  The single wearable connection row/status for the Health → Wearable section:
//  the active Fitbit→Google Health provider. Mirrors the web
//  `WearableConnectionCard` (status line + relative last-sync). Connect / Sync /
//  Disconnect affordances are deferred — the OAuth flow needs an in-app browser
//  callback that isn't wired on iOS yet (flagged in the handoff).
//

import SwiftUI

struct WearableConnectionCard: View {
    let status: APIHealthStatus?
    var isLoading: Bool = false

    private var statusText: String {
        if isLoading && status == nil { return "Checking…" }
        guard let status else { return "Not connected" }
        if status.needsReauth { return "Reconnect needed · authorization expired" }
        if status.connected { return "Connected · synced \(Self.relativeTime(status.lastSyncedAt))" }
        return "Not connected"
    }

    private var statusColor: Color {
        (status?.needsReauth ?? false) ? .destructive : .ink2
    }

    var body: some View {
        EditorialCard(padding: 18) {
            HStack(spacing: 14) {
                Image(systemName: "applewatch")
                    .font(.system(size: 20, weight: .regular))
                    .foregroundStyle(.ink2)
                    .frame(width: 44, height: 44)
                    .background(Color.surface)
                    .clipShape(RoundedRectangle(cornerRadius: 10))
                VStack(alignment: .leading, spacing: 2) {
                    Text("Fitbit (via Google)")
                        .font(.system(size: 15, weight: .semibold))
                        .foregroundStyle(.ink)
                    Text(statusText)
                        .font(.caption)
                        .foregroundStyle(statusColor)
                }
                Spacer(minLength: 8)
            }
        }
    }

    /// "just now" / "12 min ago" / "3 hr ago" / "2 d ago"; "never" when unsynced.
    static func relativeTime(_ iso: String?) -> String {
        guard let iso, let t = HealthStore.instant(iso) else { return "never" }
        let mins = Int((Date().timeIntervalSince1970 - t) / 60)
        if mins < 1 { return "just now" }
        if mins < 60 { return "\(mins) min ago" }
        let hrs = mins / 60
        if hrs < 24 { return "\(hrs) hr ago" }
        return "\(hrs / 24) d ago"
    }
}

#Preview {
    VStack(spacing: 16) {
        WearableConnectionCard(status: APIHealthStatus(
            connected: true, needsReauth: false,
            lastSyncedAt: "2026-06-23T20:00:00Z", lastSyncedActivityAt: nil, scopes: []))
        WearableConnectionCard(status: APIHealthStatus(
            connected: false, needsReauth: false,
            lastSyncedAt: nil, lastSyncedActivityAt: nil, scopes: []))
        WearableConnectionCard(status: APIHealthStatus(
            connected: true, needsReauth: true,
            lastSyncedAt: nil, lastSyncedActivityAt: nil, scopes: []))
    }
    .padding()
    .background(Color.bg)
}
