//
//  MacroBar.swift
//  GymApp
//
//  Thin labelled progress bar for macros (protein/carbs/fat).
//

import SwiftUI

struct MacroBar: View {
    let label: String
    let value: String
    let target: String
    /// 0...1
    let fraction: Double
    var tone: Color

    var body: some View {
        VStack(spacing: 4) {
            HStack {
                Text(label).font(.caption).foregroundStyle(.ink2)
                Spacer()
                HStack(spacing: 4) {
                    Text(value).font(.caption).fontWeight(.semibold).monospacedDigit()
                        .foregroundStyle(.ink)
                    Text(target).font(.caption).monospacedDigit().foregroundStyle(.ink2)
                }
            }
            GeometryReader { geo in
                ZStack(alignment: .leading) {
                    Capsule().fill(Color.fill)
                    Capsule().fill(tone)
                        .frame(width: geo.size.width * min(max(fraction, 0), 1))
                }
            }
            .frame(height: 4)
        }
    }
}
