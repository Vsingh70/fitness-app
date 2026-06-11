//
//  EditorialAppearance.swift
//  GymApp
//
//  UIKit appearance proxies for the editorial look: a transparent tab bar with
//  a hairline top, ink selected tint, tiny uppercase labels; and a matching
//  navigation bar with serif large titles. See §3.
//

import SwiftUI
import UIKit

enum EditorialAppearance {
    @MainActor
    static func apply() {
        configureTabBar()
        configureNavBar()
    }

    @MainActor
    private static func configureTabBar() {
        let appearance = UITabBarAppearance()
        appearance.configureWithTransparentBackground()
        appearance.backgroundColor = UIColor(Color.bg).withAlphaComponent(0.88)
        appearance.backgroundEffect = UIBlurEffect(style: .systemThinMaterial)
        appearance.shadowColor = UIColor(Color.hairline)

        let ink = UIColor(Color.ink)
        let ink3 = UIColor(Color.ink3)

        for item in [appearance.stackedLayoutAppearance,
                     appearance.inlineLayoutAppearance,
                     appearance.compactInlineLayoutAppearance] {
            item.selected.iconColor = ink
            item.normal.iconColor = ink3
            let selectedTitle: [NSAttributedString.Key: Any] = [
                .foregroundColor: ink,
                .font: UIFont.systemFont(ofSize: 10, weight: .semibold),
                .kern: 0.8,
            ]
            let normalTitle: [NSAttributedString.Key: Any] = [
                .foregroundColor: ink3,
                .font: UIFont.systemFont(ofSize: 10, weight: .semibold),
                .kern: 0.8,
            ]
            item.selected.titleTextAttributes = selectedTitle
            item.normal.titleTextAttributes = normalTitle
        }

        UITabBar.appearance().standardAppearance = appearance
        UITabBar.appearance().scrollEdgeAppearance = appearance
    }

    @MainActor
    private static func configureNavBar() {
        let appearance = UINavigationBarAppearance()
        appearance.configureWithTransparentBackground()
        appearance.backgroundColor = UIColor(Color.bg)
        appearance.shadowColor = .clear

        let ink = UIColor(Color.ink)
        appearance.largeTitleTextAttributes = [
            .foregroundColor: ink,
            .font: UIFont.systemFont(ofSize: 34, weight: .medium)
                .withDesign(.serif) ?? UIFont.systemFont(ofSize: 34, weight: .medium),
        ]
        appearance.titleTextAttributes = [
            .foregroundColor: ink,
            .font: UIFont.systemFont(ofSize: 17, weight: .semibold),
        ]

        UINavigationBar.appearance().standardAppearance = appearance
        UINavigationBar.appearance().scrollEdgeAppearance = appearance
        UINavigationBar.appearance().compactAppearance = appearance
        UINavigationBar.appearance().tintColor = ink
    }
}

private extension UIFont {
    /// Returns the font redrawn with the given design (e.g. serif), or nil.
    func withDesign(_ design: UIFontDescriptor.SystemDesign) -> UIFont? {
        guard let descriptor = fontDescriptor.withDesign(design) else { return nil }
        return UIFont(descriptor: descriptor, size: pointSize)
    }
}
