//
//  AddFoodSheet.swift
//  GymApp
//
//  Add-food bottom sheet (Direction A §5). Grabber, serif "Add to {meal}" title,
//  underline Search / Scan barcode tabs, search field, and result rows with a
//  circular outline +. Photo recognition was removed from the product — there is
//  no Photo tab. Camera/barcode behavior is a visual mock; the + on a row adds
//  to the target meal and dismisses.
//

import SwiftUI

struct AddFoodSheet: View {
    @Environment(\.editorialAccent) private var accent
    @Environment(\.dismiss) private var dismiss

    /// The meal this sheet logs into ("Pre-workout", "Meal 2", …).
    let mealName: String

    @State private var tab = "search"
    @State private var query = ""

    var body: some View {
        VStack(spacing: 0) {
            grabber
            header
            UnderlineSegmented(
                selection: $tab,
                options: [("search", "Search"), ("scan", "Scan barcode")],
                spacing: 24
            )
            .padding(.horizontal, 20)
            .padding(.bottom, 12)

            if tab == "scan" {
                scanTab
            } else {
                searchTab
            }
        }
        .background(Color.bg)
        .presentationDetents([.large])
        .presentationDragIndicator(.hidden)
    }

    private var grabber: some View {
        Capsule()
            .fill(Color.ink3)
            .frame(width: 36, height: 5)
            .padding(.top, 8)
            .padding(.bottom, 14)
    }

    private var header: some View {
        HStack(alignment: .firstTextBaseline) {
            Text("Add to \(mealName)")
                .font(.titleSerif).foregroundStyle(.ink)
            Spacer()
            Button("Done") { dismiss() }
                .font(.system(size: 15, weight: .semibold))
                .foregroundStyle(.ink2)
        }
        .padding(.horizontal, 20)
        .padding(.bottom, 14)
    }

    // MARK: Search

    private var searchTab: some View {
        VStack(spacing: 0) {
            HStack(spacing: 8) {
                Image(systemName: "magnifyingglass").foregroundStyle(.ink2)
                TextField("Search foods", text: $query)
                    .font(.bodyText)
            }
            .padding(.horizontal, 14).padding(.vertical, 12)
            .overlay(RoundedRectangle(cornerRadius: 8).stroke(Color.ink, lineWidth: 1.5))
            .padding(.horizontal, 20)
            .padding(.top, 12)
            .padding(.bottom, 12)

            ScrollView {
                VStack(alignment: .leading, spacing: 0) {
                    Text("Recent & favorites").kicker()
                        .padding(.horizontal, 20).padding(.bottom, 8)
                    Rectangle().fill(Color.hairline).frame(height: 1).padding(.horizontal, 20)
                    ForEach(Array(MockData.recentFoods.enumerated()), id: \.element.id) { index, food in
                        foodRow(food, last: index == MockData.recentFoods.count - 1)
                            .padding(.horizontal, 20)
                    }
                }
                .padding(.bottom, 24)
            }
            .scrollIndicators(.hidden)
        }
    }

    private func foodRow(_ food: MockData.SearchFood, last: Bool) -> some View {
        VStack(spacing: 0) {
            HStack(spacing: 12) {
                VStack(alignment: .leading, spacing: 2) {
                    Text(food.name).font(.bodyText).foregroundStyle(.ink)
                    Text(food.brand ?? "USDA")
                        .font(.caption).foregroundStyle(.ink2)
                }
                Spacer(minLength: 8)
                VStack(alignment: .trailing, spacing: 1) {
                    Text("\(food.kcalPer100)").font(.figureSmall).monospacedDigit().foregroundStyle(.ink)
                    Text("kcal / 100g").font(.caption2).foregroundStyle(.ink2)
                }
                addButton
            }
            .frame(minHeight: 56).padding(.vertical, 4)
            if !last { Rectangle().fill(Color.hairline).frame(height: 1) }
        }
    }

    private var addButton: some View {
        Button { dismiss() } label: {
            Image(systemName: "plus")
                .font(.system(size: 14, weight: .semibold))
                .foregroundStyle(accent)
                .frame(width: 30, height: 30)
                .overlay(Circle().stroke(accent, lineWidth: 1.5))
        }
        .buttonStyle(.plain)
    }

    // MARK: Scan (visual mock)

    private var scanTab: some View {
        VStack(spacing: 20) {
            ZStack {
                RoundedRectangle(cornerRadius: 14)
                    .fill(Color.ink.opacity(0.92))
                VStack(spacing: 14) {
                    Image(systemName: "barcode.viewfinder")
                        .font(.system(size: 56, weight: .thin))
                        .foregroundStyle(.bg)
                    Text("Point at a barcode")
                        .font(.footnote).foregroundStyle(Color.bg.opacity(0.7))
                }
                RoundedRectangle(cornerRadius: 6)
                    .stroke(accent, lineWidth: 2)
                    .frame(width: 220, height: 120)
            }
            .aspectRatio(3.0 / 4.0, contentMode: .fit)
            .padding(.horizontal, 20)
            .padding(.top, 12)

            Text("EAN / UPC · scans automatically")
                .font(.caption).foregroundStyle(.ink2)
            Spacer()
        }
    }
}

#Preview {
    Text("Host").sheet(isPresented: .constant(true)) {
        AddFoodSheet(mealName: "Pre-workout")
            .environment(\.editorialAccent, AccentChoice.clay.color(for: .light))
    }
}
