//
//  ScreenHeader.swift
//  GymApp
//
//  The editorial large-title header: optional uppercase kicker, serif title,
//  optional trailing control. Matches the prototype's <LargeTitle>.
//

import SwiftUI

struct ScreenHeader<Trailing: View>: View {
    let title: String
    var subtitle: String? = nil
    @ViewBuilder var trailing: Trailing

    var body: some View {
        HStack(alignment: .bottom) {
            VStack(alignment: .leading, spacing: 8) {
                if let subtitle {
                    Text(subtitle).kicker()
                }
                Text(title).font(.largeTitleSerif).foregroundStyle(.ink)
            }
            Spacer()
            trailing
        }
        .padding(.horizontal, 24)
        .padding(.top, 14)
        .padding(.bottom, 18)
    }
}

extension ScreenHeader where Trailing == EmptyView {
    init(title: String, subtitle: String? = nil) {
        self.init(title: title, subtitle: subtitle) { EmptyView() }
    }
}

/// The circular monogram / round outline button used in headers.
struct MonogramBadge: View {
    let text: String
    var size: CGFloat = 38

    var body: some View {
        Text(text)
            .font(.system(size: size * 0.37, weight: .medium, design: .serif))
            .foregroundStyle(.ink)
            .frame(width: size, height: size)
            .overlay(Circle().stroke(Color.ink, lineWidth: 1))
    }
}

struct RoundOutlineButton: View {
    let systemImage: String
    var size: CGFloat = 38
    var action: () -> Void = {}

    var body: some View {
        Button(action: action) {
            Image(systemName: systemImage)
                .font(.system(size: size * 0.45, weight: .regular))
                .foregroundStyle(.ink)
                .frame(width: size, height: size)
                .overlay(Circle().stroke(Color.ink, lineWidth: 1))
        }
        .buttonStyle(.plain)
    }
}
