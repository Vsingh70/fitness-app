//
//  MesocycleBarView.swift
//  GymApp
//
//  The mesocycle progress bar (Direction A · design .meso / .pi-meso): one cell
//  per week — completed (filled accent), current (accent outline), future
//  (hairline), deload (dashed) — over a "Week X of Y" caption. Extracted from the
//  overview so any program view can reuse it.
//

import SwiftUI

struct MesocycleBarView: View {
    @Environment(\.editorialAccent) private var accent

    let weeks: Int
    let current: Int
    let deloadWeek: Int?

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(spacing: 4) {
                ForEach(1...max(weeks, 1), id: \.self) { week in
                    cell(week: week)
                }
            }
            .frame(height: 22)
            Text("Week \(current) of \(weeks)")
                .font(.system(size: 11, weight: .semibold))
                .textCase(.uppercase).tracking(1.2)
                .foregroundStyle(.ink2)
        }
    }

    @ViewBuilder
    private func cell(week: Int) -> some View {
        let isDeload = deloadWeek == week
        let isCurrent = week == current
        let isDone = week < current
        RoundedRectangle(cornerRadius: 2)
            .fill(isDone ? accent : .clear)
            .overlay {
                if isDeload {
                    RoundedRectangle(cornerRadius: 2)
                        .strokeBorder(style: StrokeStyle(lineWidth: 1, dash: [3, 2]))
                        .foregroundStyle(.ink3)
                } else if isCurrent {
                    RoundedRectangle(cornerRadius: 2)
                        .strokeBorder(accent, lineWidth: 1.5)
                } else if !isDone {
                    RoundedRectangle(cornerRadius: 2)
                        .strokeBorder(Color.hairline, lineWidth: 1)
                }
            }
            .frame(maxWidth: .infinity)
    }
}

#Preview {
    MesocycleBarView(weeks: 8, current: 4, deloadWeek: 8)
        .padding()
        .environment(\.editorialAccent, AccentChoice.clay.color(for: .light))
}
