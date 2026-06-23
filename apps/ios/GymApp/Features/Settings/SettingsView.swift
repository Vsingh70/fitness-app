//
//  SettingsView.swift
//  GymApp
//
//  Settings tab: profile, appearance + accent picker, units, training,
//  connections, data, sign out. The accent picker and appearance toggle drive
//  the live SettingsStore so the whole app retints / reschemes immediately.
//  Mirrors ScreenSettingsIOS.
//

import SwiftUI

struct SettingsView: View {
    @Environment(SettingsStore.self) private var settings

    var body: some View {
        @Bindable var settings = settings

        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 28) {
                    ScreenHeader(title: "Settings")

                    profileCard
                    healthSection
                    appearanceSection(settings: $settings)
                    unitsSection(settings: $settings)
                    nutritionSection(settings: $settings)
                    trainingSection
                    connectionsSection
                    dataSection
                    aboutSection
                }
                .padding(.bottom, 24)
            }
            .background(Color.bg)
            .scrollIndicators(.hidden)
            .toolbar(.hidden, for: .navigationBar)
        }
    }

    // MARK: Health

    private var healthSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            SectionHeader(title: "Health")
            VStack(spacing: 0) {
                Rectangle().fill(Color.hairline).frame(height: 1)
                NavigationLink {
                    HealthView()
                } label: {
                    ChevronRow(
                        systemImage: "heart.text.square",
                        title: "Metrics & wearable",
                        detail: "Weight · steps · recovery",
                        showsSeparator: false
                    )
                }
                .buttonStyle(.plain)
                Rectangle().fill(Color.hairline).frame(height: 1)
            }
        }
        .padding(.horizontal, 20)
    }

    // MARK: Profile

    private var profileCard: some View {
        HairlineCard {
            HStack(spacing: 14) {
                MonogramBadge(text: MockData.userInitials, size: 60)
                VStack(alignment: .leading, spacing: 2) {
                    Text(MockData.userName).font(.figureSmall).foregroundStyle(.ink)
                    Text("\(MockData.userEmail) · Apple ID").font(.footnote).foregroundStyle(.ink2)
                }
                Spacer()
                Image(systemName: "chevron.right")
                    .font(.system(size: 13, weight: .semibold))
                    .foregroundStyle(.ink3)
            }
        }
        .padding(.horizontal, 20)
    }

    // MARK: Appearance

    private func appearanceSection(settings: Bindable<SettingsStore>) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            SectionHeader(title: "Appearance")
            VStack(spacing: 0) {
                Rectangle().fill(Color.hairline).frame(height: 1)
                // Accent picker
                HStack(spacing: 14) {
                    Image(systemName: "paintpalette")
                        .font(.system(size: 16)).foregroundStyle(.ink).frame(width: 24)
                    Text("Accent color").font(.bodyText).foregroundStyle(.ink)
                    Spacer(minLength: 8)
                    HStack(spacing: 8) {
                        ForEach(AccentChoice.allCases) { choice in
                            Button {
                                settings.wrappedValue.accent = choice
                            } label: {
                                Circle()
                                    .fill(choice.swatch)
                                    .frame(width: 16, height: 16)
                                    .overlay(
                                        Circle()
                                            .stroke(Color.ink, lineWidth: 1.5)
                                            .padding(-2)
                                            .opacity(settings.wrappedValue.accent == choice ? 1 : 0)
                                    )
                            }
                            .buttonStyle(.plain)
                        }
                    }
                }
                .frame(minHeight: 44)
                .padding(.vertical, 6)
                Rectangle().fill(Color.hairline).frame(height: 1)

                // Appearance mode
                HStack(spacing: 14) {
                    Image(systemName: "moon")
                        .font(.system(size: 16)).foregroundStyle(.ink).frame(width: 24)
                    Text("Appearance").font(.bodyText).foregroundStyle(.ink)
                    Spacer(minLength: 8)
                    UnderlineSegmented(
                        selection: settings.appearance,
                        options: AppearanceMode.allCases.map { ($0, $0.title) },
                        spacing: 12
                    )
                    .fixedSize()
                }
                .frame(minHeight: 44)
                .padding(.vertical, 6)
                Rectangle().fill(Color.hairline).frame(height: 1)
            }
        }
        .padding(.horizontal, 20)
    }

    // MARK: Units

    private func unitsSection(settings: Bindable<SettingsStore>) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            SectionHeader(title: "Units")
            VStack(spacing: 0) {
                Rectangle().fill(Color.hairline).frame(height: 1)
                HStack(spacing: 14) {
                    Image(systemName: "dumbbell")
                        .font(.system(size: 16)).foregroundStyle(.ink).frame(width: 24)
                    Text("Weight").font(.bodyText).foregroundStyle(.ink)
                    Spacer(minLength: 8)
                    UnderlineSegmented(
                        selection: settings.weightUnit,
                        options: WeightUnit.allCases.map { ($0, $0.title) },
                        spacing: 12
                    )
                    .fixedSize()
                }
                .frame(minHeight: 44).padding(.vertical, 6)
                Rectangle().fill(Color.hairline).frame(height: 1)
                HStack(spacing: 14) {
                    Image(systemName: "figure.walk")
                        .font(.system(size: 16)).foregroundStyle(.ink).frame(width: 24)
                    Text("Distance").font(.bodyText).foregroundStyle(.ink)
                    Spacer(minLength: 8)
                    UnderlineSegmented(
                        selection: settings.distanceUnit,
                        options: DistanceUnit.allCases.map { ($0, $0.title) },
                        spacing: 12
                    )
                    .fixedSize()
                }
                .frame(minHeight: 44).padding(.vertical, 6)
                Rectangle().fill(Color.hairline).frame(height: 1)
            }
        }
        .padding(.horizontal, 20)
    }

    // MARK: Nutrition

    private func nutritionSection(settings: Bindable<SettingsStore>) -> some View {
        let mode = Binding<NutritionMode>(
            get: { settings.wrappedValue.nutritionMode ?? .flexible },
            set: { settings.wrappedValue.nutritionMode = $0 }
        )
        return VStack(alignment: .leading, spacing: 12) {
            SectionHeader(title: "Nutrition")
            VStack(spacing: 0) {
                Rectangle().fill(Color.hairline).frame(height: 1)
                HStack(spacing: 14) {
                    Image(systemName: "fork.knife")
                        .font(.system(size: 16)).foregroundStyle(.ink).frame(width: 24)
                    Text("Tracking").font(.bodyText).foregroundStyle(.ink)
                    Spacer(minLength: 8)
                    UnderlineSegmented(
                        selection: mode,
                        options: NutritionMode.allCases.map { ($0, $0.title) },
                        spacing: 12
                    )
                    .fixedSize()
                }
                .frame(minHeight: 44).padding(.vertical, 6)
                Rectangle().fill(Color.hairline).frame(height: 1)
            }
        }
        .padding(.horizontal, 20)
    }

    // MARK: Training

    private var trainingSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            SectionHeader(title: "Training")
            VStack(spacing: 0) {
                Rectangle().fill(Color.hairline).frame(height: 1)
                ChevronRow(systemImage: "list.bullet", title: "Active program", detail: "PPL · W4")
                ChevronRow(systemImage: "timer", title: "Default rest", detail: "2:00")
                ChevronRow(systemImage: "bolt", title: "Plate set", detail: "25/20/15/10/5/2.5",
                           showsSeparator: false)
                Rectangle().fill(Color.hairline).frame(height: 1)
            }
        }
        .padding(.horizontal, 20)
    }

    // MARK: Connections

    private var connectionsSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            SectionHeader(title: "Connected services")
            VStack(spacing: 0) {
                Rectangle().fill(Color.hairline).frame(height: 1)
                ConnectionRow(systemImage: "applewatch", title: "Fitbit",
                              detail: "Synced 2m ago", isOn: true)
                ConnectionRow(systemImage: "heart.text.square", title: "Apple Health",
                              detail: "Not connected", isOn: false)
                ConnectionRow(systemImage: "bolt.horizontal", title: "Ollama (insights)",
                              detail: "Local · healthy", isOn: true, showsSeparator: false)
                Rectangle().fill(Color.hairline).frame(height: 1)
            }
        }
        .padding(.horizontal, 20)
    }

    // MARK: Data

    private var dataSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            SectionHeader(title: "Data")
            VStack(spacing: 0) {
                Rectangle().fill(Color.hairline).frame(height: 1)
                ChevronRow(systemImage: "square.and.arrow.up", title: "Export CSV")
                ChevronRow(systemImage: "icloud.and.arrow.up", title: "Cloud backup",
                           detail: "Off", showsSeparator: false)
                Rectangle().fill(Color.hairline).frame(height: 1)
            }
        }
        .padding(.horizontal, 20)
    }

    // MARK: About / sign out

    private var aboutSection: some View {
        VStack(spacing: 0) {
            VStack(spacing: 0) {
                Rectangle().fill(Color.hairline).frame(height: 1)
                ChevronRow(title: "About gym")
                GroupedRow(title: "Sign out", titleColor: .destructive, showsSeparator: false) {
                    EmptyView()
                }
                Rectangle().fill(Color.hairline).frame(height: 1)
            }
            Text(MockData.appVersion)
                .font(.caption).foregroundStyle(.ink2)
                .frame(maxWidth: .infinity)
                .padding(.vertical, 14)
        }
        .padding(.horizontal, 20)
    }
}

/// A row whose trailing accessory is an ink-tinted toggle.
private struct ConnectionRow: View {
    let systemImage: String
    let title: String
    let detail: String
    @State var isOn: Bool
    var showsSeparator: Bool = true

    var body: some View {
        VStack(spacing: 0) {
            HStack(spacing: 14) {
                Image(systemName: systemImage)
                    .font(.system(size: 16)).foregroundStyle(.ink).frame(width: 24)
                VStack(alignment: .leading, spacing: 1) {
                    Text(title).font(.bodyText).foregroundStyle(.ink)
                    Text(detail).font(.caption).foregroundStyle(.ink2)
                }
                Spacer(minLength: 8)
                Toggle("", isOn: $isOn)
                    .labelsHidden()
                    .tint(.ink)
            }
            .frame(minHeight: 44)
            .padding(.vertical, 6)
            if showsSeparator {
                Rectangle().fill(Color.hairline).frame(height: 1)
            }
        }
    }
}

#Preview {
    SettingsView()
        .environment(SettingsStore())
        .environment(\.editorialAccent, AccentChoice.clay.color(for: .light))
}
