//
//  NutritionStore.swift
//  GymApp
//
//  Live, API-backed store for the Direction A "log-first" Nutrition surface.
//  Mirrors the shipped web `/nutrition` day page (calorie masthead, quick-add
//  search, P/C/F strip, recent chips, meals) and maps everything into the
//  Phase-1 view structs in `MockData.swift` so the screens stay declarative.
//
//  Endpoints (grounded in live dev responses, env `dev`):
//   - `GET  /v1/nutrition/day?date=`   → totals + per-meal (the day's meals).
//   - `GET  /v1/nutrition/targets`     → kcal/P/C/F targets (409 when the profile
//                                        is incomplete → "set up your plan").
//   - `GET  /v1/foods/recent`          → one-tap recent chips.
//   - `GET  /v1/foods/search?q=`       → the Add-food sheet search.
//   - `GET  /v1/foods/barcode/{code}`  → barcode resolve → a single food.
//   - `POST /v1/meals`                 → create a (flexible) meal.
//   - `POST /v1/meals/{id}/items`      → log an item into a meal.
//
//  Design notes (mirrors ProgramsStore / TodayStore):
//   - Injected with an `APIClient` + `AuthService`. When nil (SwiftUI previews)
//     the store stays offline and seeds from `MockData` so canvases render.
//   - Food names referenced by logged items aren't embedded in the day summary,
//     so the store resolves them best-effort via `GET /v1/foods/{id}` into a
//     cache, falling back to "Food" when unavailable (matches the web).
//   - The day summary's `per_meal` is the single source of truth for the day;
//     no separate `/meals` range fetch is needed.
//   - Never crashes on a network/decode error: failures land in `loadState`;
//     each surface degrades independently.
//

import SwiftUI

@MainActor
@Observable
final class NutritionStore {

    enum LoadState: Equatable {
        case idle
        case loading
        case loaded
        case failed(String)
    }

    // MARK: View-facing state (the screens read these via derived values)

    /// The day's totals + logged meals.
    private(set) var day: APIDaySummary?
    /// kcal/P/C/F targets, nil when the profile is incomplete (409).
    private(set) var targets: APIMealPlanTargets?
    /// One-tap recent chips.
    private(set) var recent: [APIRecentFood] = []

    private(set) var loadState: LoadState = .idle
    /// True while a quick log (recent chip / picked food) is in flight.
    private(set) var isLogging = false

    // MARK: Dependencies

    private let client: APIClient?
    private let auth: AuthService?

    /// Best-effort food-name cache (food_id → name) so logged-item rows render a
    /// real label rather than "Food".
    private var foodNames: [String: String] = [:]

    /// The ISO day the store is showing (today, in the device's local zone).
    private let isoDay: String

    // MARK: Init

    /// Live init — used by the app shell.
    init(client: APIClient, auth: AuthService) {
        self.client = client
        self.auth = auth
        self.isoDay = Self.isoToday()
    }

    /// Offline init — used by SwiftUI previews. Seeds sample data so the canvas
    /// renders without a network.
    init(preview: Bool) {
        self.client = nil
        self.auth = nil
        self.isoDay = "2026-06-23"
        self.day = APIDaySummary(
            date: "2026-06-23",
            totals: APIDayMacros(
                kcal: "1620.00", proteinG: "134.00", carbsG: "168.00",
                fatG: "51.00", fiberG: "24.00"
            )
        )
        self.targets = APIMealPlanTargets(
            targetKcal: "2680", targetProteinG: "200", targetCarbsG: "300", targetFatG: "80"
        )
        self.loadState = .loaded
    }

    var hasResolved: Bool {
        switch loadState {
        case .loaded, .failed: return true
        case .idle, .loading: return false
        }
    }

    // MARK: - Load

    /// Fetch the day summary, targets, and recent foods. No-op offline (previews).
    /// Each surface degrades independently — a missing target doesn't blank meals.
    func load() async {
        guard let client else { return }
        await auth?.ensureSignedIn()
        loadState = .loading

        day = try? await client.request(.get, "/nutrition/day?date=\(isoDay)")
        targets = try? await client.request(.get, "/nutrition/targets")
        if let list: APIRecentFoodList = try? await client.request(.get, "/foods/recent") {
            recent = list.items
        }

        await resolveFoodNames()
        loadState = .loaded
    }

    /// Re-fetch just the day (after a log) so totals + rows update.
    private func reloadDay() async {
        guard let client else { return }
        day = try? await client.request(.get, "/nutrition/day?date=\(isoDay)")
        if let list: APIRecentFoodList = try? await client.request(.get, "/foods/recent") {
            recent = list.items
        }
        await resolveFoodNames()
    }

    /// Resolve any not-yet-cached food ids referenced by the day's items.
    private func resolveFoodNames() async {
        guard let client, let day else { return }
        let referenced = Set(day.perMeal.flatMap { $0.items }.map(\.foodId))
        let missing = referenced.subtracting(foodNames.keys)
        for id in missing {
            if let food: APIFood = try? await client.request(.get, "/foods/\(id)") {
                foodNames[id] = food.name
            }
        }
    }

    // MARK: - Search / barcode

    /// `GET /v1/foods/search?q=` (first page). Empty/whitespace query → []. The
    /// Add-food sheet renders the returned foods as result rows.
    func searchFoods(_ query: String) async -> [APIFood] {
        let q = query.trimmingCharacters(in: .whitespacesAndNewlines)
        guard let client, !q.isEmpty else { return [] }
        let encoded = q.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? q
        let list: APIFoodList? = try? await client.request(.get, "/foods/search?q=\(encoded)&limit=25")
        return list?.items ?? []
    }

    /// `GET /v1/foods/barcode/{barcode}` → a single resolved food (or nil when
    /// not found / off the device's scanner path).
    func resolveBarcode(_ barcode: String) async -> APIFood? {
        let code = barcode.trimmingCharacters(in: .whitespacesAndNewlines)
        guard let client, !code.isEmpty else { return nil }
        let encoded = code.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) ?? code
        return try? await client.request(.get, "/foods/barcode/\(encoded)")
    }

    // MARK: - Logging

    /// Log a food into the meal named `mealName`. Resolves the target meal (an
    /// existing logged meal with that name, else a fresh flexible meal), POSTs the
    /// item, then reloads the day. `amount`/`unit`/`servingId` come from the
    /// Add-food sheet (defaulting to 100 g). Returns true on success.
    @discardableResult
    func logFood(
        _ food: APIFood,
        into mealName: String,
        amount: Double = 100,
        unit: String = "g",
        servingId: String? = nil
    ) async -> Bool {
        guard let client else { return false }
        isLogging = true
        defer { isLogging = false }
        // Cache the name eagerly so the row label is correct after reload.
        foodNames[food.id] = food.name
        do {
            let mealID = try await ensureMeal(named: mealName)
            let body = APIMealItemCreate(
                foodId: food.id, amount: amount, unit: unit, servingId: servingId
            )
            let _: APIMealItem = try await client.request(
                .post, "/meals/\(mealID)/items", body: body
            )
            await reloadDay()
            return true
        } catch {
            return false
        }
    }

    /// One-tap re-log of a recent food, reproducing its last logging.
    @discardableResult
    func logRecent(_ food: APIRecentFood, into mealName: String) async -> Bool {
        guard let client else { return false }
        isLogging = true
        defer { isLogging = false }
        foodNames[food.foodId] = food.name
        // Reproduce the last logging: amount+unit (or grams as the fallback).
        let amount = Double(food.lastAmount ?? food.lastGrams) ?? Double(food.lastGrams) ?? 0
        let servingId = food.lastUnit == "serving" ? food.lastServingId : nil
        do {
            let mealID = try await ensureMeal(named: mealName)
            let body = APIMealItemCreate(
                foodId: food.foodId, amount: amount, unit: food.lastUnit, servingId: servingId
            )
            let _: APIMealItem = try await client.request(
                .post, "/meals/\(mealID)/items", body: body
            )
            await reloadDay()
            return true
        } catch {
            return false
        }
    }

    /// Create a fresh, empty flexible meal (the "+ Add meal" action), then reload
    /// so the new (empty) row appears. Returns the new meal's display name.
    @discardableResult
    func addEmptyMeal() async -> String? {
        guard let client else { return nil }
        let name = nextFlexibleMealName
        do {
            let body = APIMealCreate(eatenAt: Self.nowInstant(), mealType: "snack", name: nil)
            let _: APIMeal = try await client.request(.post, "/meals", body: body)
            await reloadDay()
            return name
        } catch {
            return nil
        }
    }

    /// Resolve a meal name to a concrete logged meal id, creating a flexible meal
    /// when none with that name exists yet. Plan slots and flexible "Meal N" rows
    /// both resolve here; a server `name` is set only for explicitly-named meals
    /// (the log-first UI leaves flexible names implicit → server name `null`).
    private func ensureMeal(named mealName: String) async throws -> String {
        guard let client else { throw APIError.invalidURL }
        // Match an existing logged meal by display name (flexible "Meal N" or a
        // server-set name).
        if let existing = existingMealId(for: mealName) { return existing }
        // Create a flexible meal. Implicit "Meal N" names stay server-null so the
        // day re-numbers them like the web; an explicit slot name is sent through.
        let sendName = isImplicitFlexibleName(mealName) ? nil : mealName
        let body = APIMealCreate(eatenAt: Self.nowInstant(), mealType: "snack", name: sendName)
        let meal: APIMeal = try await client.request(.post, "/meals", body: body)
        return meal.id
    }

    /// The logged meal id backing a display name, if one exists today. Flexible
    /// meals render as "Meal 1..n" (server name null), so an implicit name maps to
    /// the meal at that ordinal; a server-named meal matches by name.
    private func existingMealId(for mealName: String) -> String? {
        let meals = orderedMeals
        if let index = implicitFlexibleIndex(mealName), index < meals.count {
            return meals[index].mealId
        }
        return meals.first {
            mealDisplayName(for: $0).caseInsensitiveCompare(mealName) == .orderedSame
        }?.mealId
    }

    // MARK: - Derived: masthead

    var kcalConsumed: Int { Int(Double(day?.totals.kcal ?? "0") ?? 0) }
    var kcalTarget: Int? { targets.flatMap { Int(Double($0.targetKcal) ?? 0) } }
    var kcalRemaining: Int? { kcalTarget.map { max($0 - kcalConsumed, 0) } }

    /// "Tuesday · May 27"-style kicker for the masthead, localized to today.
    var todayKicker: String {
        let fmt = DateFormatter()
        fmt.dateFormat = "EEEE · MMMM d"
        return fmt.string(from: Date())
    }

    // MARK: - Derived: P/C/F strip

    /// The macro lines (Protein / Carbs / Fat) consumed vs. target. Targets fall
    /// back to 0 when the profile is incomplete (the row still renders).
    var macroLines: [MockData.MacroLine] {
        [
            MockData.MacroLine(
                label: "Protein",
                value: Int(Double(day?.totals.proteinG ?? "0") ?? 0),
                target: Int(Double(targets?.targetProteinG ?? "0") ?? 0)
            ),
            MockData.MacroLine(
                label: "Carbs",
                value: Int(Double(day?.totals.carbsG ?? "0") ?? 0),
                target: Int(Double(targets?.targetCarbsG ?? "0") ?? 0)
            ),
            MockData.MacroLine(
                label: "Fat",
                value: Int(Double(day?.totals.fatG ?? "0") ?? 0),
                target: Int(Double(targets?.targetFatG ?? "0") ?? 0)
            ),
        ]
    }

    // MARK: - Derived: recent chips

    /// Recent foods mapped to the Add-food sheet / chip view struct.
    var recentChips: [MockData.SearchFood] {
        recent.map {
            MockData.SearchFood(
                name: $0.name,
                brand: $0.brand,
                kcalPer100: Int(Double($0.lastKcal ?? "0") ?? 0),
                protein: Int(Double($0.lastProteinG ?? "0") ?? 0)
            )
        }
    }

    // MARK: - Derived: meals (flexible)

    /// The day's logged meals, ordered by `eaten_at` (oldest → newest) so the
    /// flexible "Meal 1..n" numbering is stable, mirroring the web.
    var orderedMeals: [APIDayPerMeal] {
        (day?.perMeal ?? []).sorted { $0.eatenAt < $1.eatenAt }
    }

    /// The logged meals mapped to the Phase-1 `MockData.Meal` view struct (one row
    /// per meal). Flexible names render as "Meal N"; item labels come from the
    /// best-effort food-name cache.
    var flexibleMeals: [MockData.Meal] {
        orderedMeals.enumerated().map { index, meal in
            MockData.Meal(
                name: "Meal \(index + 1)",
                at: Self.clock(from: meal.eatenAt),
                kcal: Int(Double(meal.totals.kcal) ?? 0),
                protein: Int(Double(meal.totals.proteinG) ?? 0),
                carbs: Int(Double(meal.totals.carbsG) ?? 0),
                fat: Int(Double(meal.totals.fatG) ?? 0),
                items: meal.items.map {
                    MockData.FoodItem(
                        name: foodNames[$0.foodId] ?? "Food",
                        kcal: Int(Double($0.kcal ?? "0") ?? 0),
                        source: Self.source(for: $0.unit)
                    )
                }
            )
        }
    }

    /// True when no meals are logged today (drives the empty hint).
    var isEmpty: Bool { orderedMeals.isEmpty }

    /// The display name for the meal a quick-add / chip should land in: the most
    /// recent logged meal, else the first new "Meal 1".
    var defaultAddMealName: String {
        if let last = orderedMeals.last {
            let index = orderedMeals.count - 1
            return mealDisplayName(for: last, atIndex: index)
        }
        return "Meal 1"
    }

    /// The name the next "+ Add meal" would create.
    var nextFlexibleMealName: String { "Meal \(orderedMeals.count + 1)" }

    // MARK: - Mapping helpers

    private func mealDisplayName(for meal: APIDayPerMeal) -> String {
        let index = orderedMeals.firstIndex { $0.mealId == meal.mealId } ?? 0
        return mealDisplayName(for: meal, atIndex: index)
    }

    private func mealDisplayName(for meal: APIDayPerMeal, atIndex index: Int) -> String {
        "Meal \(index + 1)"
    }

    /// Implicit "Meal N" names map to a 0-based ordinal; anything else is explicit.
    private func implicitFlexibleIndex(_ name: String) -> Int? {
        let lower = name.lowercased()
        guard lower.hasPrefix("meal ") else { return nil }
        let suffix = lower.dropFirst("meal ".count)
        guard let n = Int(suffix), n >= 1 else { return nil }
        return n - 1
    }

    private func isImplicitFlexibleName(_ name: String) -> Bool {
        implicitFlexibleIndex(name) != nil
    }

    private static func source(for unit: String) -> MockData.FoodSource {
        switch unit {
        case "serving": return .favorite
        default: return .manual
        }
    }

    /// "07:30" wall-clock from an ISO-8601 instant (device local zone).
    private static func clock(from iso: String) -> String {
        guard let date = isoFormatter.date(from: iso) ?? isoFractional.date(from: iso) else {
            return "—"
        }
        let fmt = DateFormatter()
        fmt.dateFormat = "HH:mm"
        return fmt.string(from: date)
    }

    private static func isoToday() -> String {
        let fmt = DateFormatter()
        fmt.locale = Locale(identifier: "en_US_POSIX")
        fmt.dateFormat = "yyyy-MM-dd"
        return fmt.string(from: Date())
    }

    /// An ISO-8601 instant for "now" (meal `eaten_at`).
    private static func nowInstant() -> String {
        isoFormatter.string(from: Date())
    }

    private static let isoFormatter: ISO8601DateFormatter = {
        let f = ISO8601DateFormatter()
        f.formatOptions = [.withInternetDateTime]
        return f
    }()

    private static let isoFractional: ISO8601DateFormatter = {
        let f = ISO8601DateFormatter()
        f.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        return f
    }()
}
