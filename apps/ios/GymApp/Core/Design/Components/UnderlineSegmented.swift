//
//  UnderlineSegmented.swift
//  GymApp
//
//  Editorial segmented control: underline tabs, NOT a filled pill.
//  Each label uppercase/tracked 12pt; selected gets a 1.5pt ink underline;
//  the row sits on a hairline bottom rule. See §3.
//

import SwiftUI

struct UnderlineSegmented<Value: Hashable>: View {
    @Binding var selection: Value
    let options: [(value: Value, title: String)]
    var spacing: CGFloat = 18

    var body: some View {
        HStack(spacing: spacing) {
            ForEach(options, id: \.value) { option in
                let isOn = option.value == selection
                Button {
                    selection = option.value
                } label: {
                    Text(option.title)
                        .font(.system(size: 12, weight: .semibold))
                        .textCase(.uppercase)
                        .tracking(0.96)
                        .foregroundStyle(isOn ? Color.ink : Color.ink2)
                        .padding(.vertical, 6)
                        .overlay(alignment: .bottom) {
                            Rectangle()
                                .fill(isOn ? Color.ink : .clear)
                                .frame(height: 1.5)
                        }
                }
                .buttonStyle(.plain)
            }
        }
        .overlay(alignment: .bottom) {
            Rectangle().fill(Color.hairline).frame(height: 1)
        }
    }
}

#Preview {
    struct Demo: View {
        @State private var sel = "4w"
        var body: some View {
            UnderlineSegmented(
                selection: $sel,
                options: [("1w", "1w"), ("4w", "4w"), ("3m", "3m")]
            )
            .padding()
            .background(Color.bg)
        }
    }
    return Demo()
}
