//
//  MesocycleBarView.swift
//  GymApp
//
//  The mesocycle progress bar (Direction A · design .meso / .pi-meso): one cell
//  per microcycle repetition — completed (filled accent), current (accent
//  outline), future (hairline) — plus a trailing dashed deload cell when
//  auto-deload is on, over a "Cycle X of Y" caption. Extracted from the overview
//  so any program view can reuse it.
//

import SwiftUI

struct MesocycleBarView: View {
    @Environment(\.editorialAccent) private var accent

    /// Microcycle repetitions in the mesocycle (deload excluded).
    let repetitions: Int
    /// Current repetition (1-based).
    let current: Int
    /// Whether a trailing deload microcycle is appended.
    let autoDeload: Bool
    /// Whether we're currently inside the deload microcycle.
    let inDeload: Bool

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(spacing: 4) {
                ForEach(1...max(repetitions, 1), id: \.self) { rep in
                    cell(rep: rep)
                }
                if autoDeload {
                    deloadCell
                }
            }
            .frame(height: 22)
            Text("Cycle \(current) of \(repetitions)")
                .font(.system(size: 11, weight: .semibold))
                .textCase(.uppercase).tracking(1.2)
                .foregroundStyle(.ink2)
        }
    }

    @ViewBuilder
    private func cell(rep: Int) -> some View {
        let isCurrent = !inDeload && rep == current
        let isDone = inDeload || rep < current
        RoundedRectangle(cornerRadius: 2)
            .fill(isDone ? accent : .clear)
            .overlay {
                if isCurrent {
                    RoundedRectangle(cornerRadius: 2)
                        .strokeBorder(accent, lineWidth: 1.5)
                } else if !isDone {
                    RoundedRectangle(cornerRadius: 2)
                        .strokeBorder(Color.hairline, lineWidth: 1)
                }
            }
            .frame(maxWidth: .infinity)
    }

    private var deloadCell: some View {
        RoundedRectangle(cornerRadius: 2)
            .fill(.clear)
            .overlay {
                RoundedRectangle(cornerRadius: 2)
                    .strokeBorder(
                        inDeload ? accent : Color.ink3,
                        style: StrokeStyle(lineWidth: inDeload ? 1.5 : 1, dash: [3, 2])
                    )
            }
            .frame(maxWidth: .infinity)
    }
}

#Preview {
    MesocycleBarView(repetitions: 4, current: 2, autoDeload: true, inDeload: false)
        .padding()
        .environment(\.editorialAccent, AccentChoice.clay.color(for: .light))
}
