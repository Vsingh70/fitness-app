//
//  AddFoodSheet.swift
//  GymApp
//
//  Add-food bottom sheet (Direction A §5). Grabber, serif "Add to {meal}" title,
//  underline Search / Scan barcode tabs, search field, and result rows with a
//  circular outline +. Photo recognition was removed from the product — there is
//  no Photo tab.
//
//  Wired to live data via `NutritionStore`: the search field hits
//  `GET /v1/foods/search`; the barcode field resolves via
//  `GET /v1/foods/barcode/{code}`. The + on a row logs the food into the target
//  meal (`POST /v1/meals` + `/items`) and dismisses. When the query is empty the
//  list falls back to the user's recent foods.
//

import SwiftUI

struct AddFoodSheet: View {
    @Environment(\.editorialAccent) private var accent
    @Environment(\.dismiss) private var dismiss
    @Environment(NutritionStore.self) private var store

    /// The meal this sheet logs into ("Meal 1", "Pre-workout", …).
    let mealName: String

    @State private var tab = "search"
    @State private var query = ""
    @State private var results: [APIFood] = []
    @State private var isSearching = false

    /// Barcode entry (the device camera/scanner is out of scope for the visual
    /// pass; an entered EAN/UPC resolves a food via the API).
    @State private var barcode = ""
    @State private var scanResult: APIFood?
    @State private var scanState: ScanState = .idle

    private enum ScanState: Equatable {
        case idle, resolving, notFound
    }

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
                    .autocorrectionDisabled()
                    .textInputAutocapitalization(.never)
                if isSearching {
                    ProgressView().controlSize(.small)
                }
            }
            .padding(.horizontal, 14).padding(.vertical, 12)
            .overlay(RoundedRectangle(cornerRadius: 8).stroke(Color.ink, lineWidth: 1.5))
            .padding(.horizontal, 20)
            .padding(.top, 12)
            .padding(.bottom, 12)

            ScrollView {
                VStack(alignment: .leading, spacing: 0) {
                    let trimmed = query.trimmingCharacters(in: .whitespaces)
                    if trimmed.isEmpty {
                        recentSection
                    } else {
                        resultsSection
                    }
                }
                .padding(.bottom, 24)
            }
            .scrollIndicators(.hidden)
        }
        // Debounced live search: re-run when the query settles.
        .task(id: query) {
            let trimmed = query.trimmingCharacters(in: .whitespaces)
            guard !trimmed.isEmpty else {
                results = []
                isSearching = false
                return
            }
            isSearching = true
            try? await Task.sleep(for: .milliseconds(280))
            if Task.isCancelled { return }
            let found = await store.searchFoods(trimmed)
            if Task.isCancelled { return }
            results = found
            isSearching = false
        }
    }

    @ViewBuilder
    private var recentSection: some View {
        Text("Recent & favorites").kicker()
            .padding(.horizontal, 20).padding(.bottom, 8)
        Rectangle().fill(Color.hairline).frame(height: 1).padding(.horizontal, 20)
        if store.recent.isEmpty {
            Text("Search to find a food, or scan a barcode.")
                .font(.footnote).foregroundStyle(.ink3)
                .padding(.horizontal, 20).padding(.top, 16)
        } else {
            ForEach(Array(store.recent.enumerated()), id: \.element.id) { index, food in
                recentRow(food, last: index == store.recent.count - 1)
                    .padding(.horizontal, 20)
            }
        }
    }

    @ViewBuilder
    private var resultsSection: some View {
        if results.isEmpty, !isSearching {
            Text("No foods match “\(query)”.")
                .font(.footnote).foregroundStyle(.ink3)
                .padding(.horizontal, 20).padding(.top, 16)
        } else {
            ForEach(Array(results.enumerated()), id: \.element.id) { index, food in
                foodRow(food, last: index == results.count - 1)
                    .padding(.horizontal, 20)
            }
        }
    }

    private func foodRow(_ food: APIFood, last: Bool) -> some View {
        VStack(spacing: 0) {
            HStack(spacing: 12) {
                VStack(alignment: .leading, spacing: 2) {
                    Text(food.name).font(.bodyText).foregroundStyle(.ink)
                    Text(food.brand ?? sourceLabel(food.source))
                        .font(.caption).foregroundStyle(.ink2)
                }
                Spacer(minLength: 8)
                VStack(alignment: .trailing, spacing: 1) {
                    Text("\(Int(Double(food.kcalPer100g ?? "0") ?? 0))")
                        .font(.figureSmall).monospacedDigit().foregroundStyle(.ink)
                    Text("kcal / 100g").font(.caption2).foregroundStyle(.ink2)
                }
                addButton { await store.logFood(food, into: mealName) }
            }
            .frame(minHeight: 56).padding(.vertical, 4)
            if !last { Rectangle().fill(Color.hairline).frame(height: 1) }
        }
    }

    private func recentRow(_ food: APIRecentFood, last: Bool) -> some View {
        VStack(spacing: 0) {
            HStack(spacing: 12) {
                VStack(alignment: .leading, spacing: 2) {
                    Text(food.name).font(.bodyText).foregroundStyle(.ink)
                    Text(food.brand ?? sourceLabel(food.source))
                        .font(.caption).foregroundStyle(.ink2)
                }
                Spacer(minLength: 8)
                VStack(alignment: .trailing, spacing: 1) {
                    Text("\(Int(Double(food.lastKcal ?? "0") ?? 0))")
                        .font(.figureSmall).monospacedDigit().foregroundStyle(.ink)
                    Text("kcal").font(.caption2).foregroundStyle(.ink2)
                }
                addButton { await store.logRecent(food, into: mealName) }
            }
            .frame(minHeight: 56).padding(.vertical, 4)
            if !last { Rectangle().fill(Color.hairline).frame(height: 1) }
        }
    }

    private func addButton(_ action: @escaping () async -> Bool) -> some View {
        Button {
            Task {
                let ok = await action()
                if ok { dismiss() }
            }
        } label: {
            Image(systemName: "plus")
                .font(.system(size: 14, weight: .semibold))
                .foregroundStyle(accent)
                .frame(width: 30, height: 30)
                .overlay(Circle().stroke(accent, lineWidth: 1.5))
        }
        .buttonStyle(.plain)
        .disabled(store.isLogging)
    }

    private func sourceLabel(_ source: String) -> String {
        switch source {
        case "usda": return "USDA"
        case "off": return "Open Food Facts"
        case "user": return "Your foods"
        default: return "Custom"
        }
    }

    // MARK: Scan (barcode resolve)

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

            // Manual entry path (the live camera scanner is out of scope here).
            HStack(spacing: 8) {
                Image(systemName: "number").foregroundStyle(.ink2)
                TextField("Enter EAN / UPC", text: $barcode)
                    .font(.bodyText)
                    .keyboardType(.numberPad)
                Button("Find") { Task { await resolveBarcode() } }
                    .font(.system(size: 14, weight: .semibold))
                    .foregroundStyle(accent)
                    .disabled(barcode.trimmingCharacters(in: .whitespaces).isEmpty || scanState == .resolving)
            }
            .padding(.horizontal, 14).padding(.vertical, 12)
            .overlay(RoundedRectangle(cornerRadius: 8).stroke(Color.ink, lineWidth: 1.5))
            .padding(.horizontal, 20)

            scanStatus
            Spacer()
        }
    }

    @ViewBuilder
    private var scanStatus: some View {
        switch scanState {
        case .idle:
            Text("EAN / UPC · enter a code to resolve")
                .font(.caption).foregroundStyle(.ink2)
        case .resolving:
            ProgressView().controlSize(.small)
        case .notFound:
            Text("No match for that barcode.")
                .font(.caption).foregroundStyle(.destructive)
        }

        if let food = scanResult {
            VStack(spacing: 0) {
                Rectangle().fill(Color.hairline).frame(height: 1)
                foodRow(food, last: true)
            }
            .padding(.horizontal, 20)
        }
    }

    private func resolveBarcode() async {
        scanState = .resolving
        scanResult = nil
        if let food = await store.resolveBarcode(barcode) {
            scanResult = food
            scanState = .idle
        } else {
            scanState = .notFound
        }
    }
}

#Preview {
    Text("Host").sheet(isPresented: .constant(true)) {
        AddFoodSheet(mealName: "Meal 1")
            .environment(NutritionStore(preview: true))
            .environment(\.editorialAccent, AccentChoice.clay.color(for: .light))
    }
}
