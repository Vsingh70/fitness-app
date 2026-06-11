//
//  MiniSegmented.swift
//  GymApp
//
//  Compact ink-filled segmented control — the prototype's `.mini-seg`. The
//  active segment is an ink fill with paper text; the track is hairline-bordered.
//  Distinct from UnderlineSegmented (which uses underlines, not fills). Used for
//  the builder's global RPE/RIR/Off and per-exercise Range/Target toggles.
//

import SwiftUI

struct MiniSegmented<Value: Hashable>: View {
    @Binding var selection: Value
    let options: [(value: Value, title: String)]

    var body: some View {
        HStack(spacing: 0) {
            ForEach(options, id: \.value) { option in
                let isOn = option.value == selection
                Button {
                    selection = option.value
                } label: {
                    Text(option.title)
                        .font(.system(size: 12, weight: .semibold))
                        .textCase(.uppercase)
                        .tracking(0.8)
                        .foregroundStyle(isOn ? Color.bg : Color.ink2)
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 8)
                        .background(isOn ? Color.ink : .clear)
                }
                .buttonStyle(.plain)
            }
        }
        .clipShape(RoundedRectangle(cornerRadius: 6))
        .overlay(RoundedRectangle(cornerRadius: 6).stroke(Color.hairline, lineWidth: 1))
    }
}

#Preview {
    struct Demo: View {
        @State private var a = MockData.IntensityMode.rpe
        @State private var b = MockData.RepMode.range
        var body: some View {
            VStack(spacing: 20) {
                MiniSegmented(
                    selection: $a,
                    options: MockData.IntensityMode.allCases.map { ($0, $0.title) }
                )
                MiniSegmented(
                    selection: $b,
                    options: MockData.RepMode.allCases.map { ($0, $0.title) }
                )
            }
            .padding()
            .background(Color.bg)
        }
    }
    return Demo()
}
