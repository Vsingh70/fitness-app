//
//  APIModels.swift
//  GymApp
//
//  Codable mirrors of the backend JSON, grounded in live dev responses
//  (env `dev`, DB migration 0027). Snake-case keys are mapped via
//  `JSONDecoder.keyDecodingStrategy = .convertFromSnakeCase` in `APIClient`,
//  so property names here are the camelCase of the wire names.
//
//  These are the WIRE shapes only. Mapping into the Phase-1 view structs in
//  `MockData.swift` happens in the store layer (Task B) so the views never change.
//

import Foundation

// MARK: - Auth

/// `POST /v1/auth/dev` and `POST /v1/auth/refresh` both return this (`TokenPair`).
struct APITokenPair: Codable, Sendable {
    let accessToken: String
    let refreshToken: String
    let tokenType: String?
    let expiresIn: Int
}

// MARK: - Programs (list)

/// `GET /v1/programs` → `{ items, next_cursor }` (cursor pagination per
/// api-conventions.md). `next_cursor` is null when the page is the last.
struct APIProgramList: Codable, Sendable {
    let items: [APIProgramListItem]
    let nextCursor: String?
}

/// A row in the programs list. Lighter than the full `APIProgram`.
struct APIProgramListItem: Codable, Sendable, Identifiable {
    let id: String
    let name: String
    let goal: String?
    let microcycleLength: Int
    let mesocycleLengthMicrocycles: Int
    let source: String?
    let isActive: Bool
    let activatedAt: String?
    let createdAt: String?
}

// MARK: - Program (detail)

/// `GET /v1/programs/{id}` and `POST /v1/program-templates/{slug}/copy` → full program.
struct APIProgram: Codable, Sendable, Identifiable {
    let id: String
    let name: String
    let description: String?
    let goal: String?
    let microcycleLength: Int
    let source: String?
    let templateId: String?
    let isActive: Bool
    let activatedAt: String?
    let mesocycleLengthMicrocycles: Int
    let autoDeload: Bool?
    let periodizationMode: String?
    let autoDeloadOnStall: Bool?
    let intensityMode: String?
    let days: [APIProgramSlot]
    let createdAt: String?
}

/// A day/slot in the microcycle. `slotIndex` is 0-based; rest days carry no exercises.
struct APIProgramSlot: Codable, Sendable, Identifiable {
    let id: String
    let slotIndex: Int
    let name: String?
    let isRestDay: Bool
    let exercises: [APIProgramExercise]
}

/// One programmed exercise (a `program_day_exercise` row). `targetRpeLow`/`High`
/// arrive as decimal *strings* on the wire (e.g. `"7.0"`); convenience accessors
/// parse them. `exerciseId` references the exercise library (not embedded yet).
struct APIProgramExercise: Codable, Sendable, Identifiable {
    let id: String
    let exerciseId: String
    let position: Int
    let targetSets: Int?
    let targetRepsLow: Int?
    let targetRepsHigh: Int?
    let targetRpeLow: String?
    let targetRpeHigh: String?
    let targetRirLow: Int?
    let targetRirHigh: Int?
    let restSeconds: Int?
    let repMode: String?
    let progressionStrategy: String?
    let notes: String?

    var targetRpeLowValue: Double? { targetRpeLow.flatMap(Double.init) }
    var targetRpeHighValue: Double? { targetRpeHigh.flatMap(Double.init) }
}

// MARK: - Position

/// `GET /v1/programs/{id}/position` → where the user is in the mesocycle right now.
struct APIPosition: Codable, Sendable {
    let currentSlotIndex: Int
    let currentMicrocycleNumber: Int
    let currentRepetition: Int
    let mesocycleLengthMicrocycles: Int
    let inDeload: Bool
    let todaySlot: APIProgramSlot?
    let isRestDay: Bool
    let nextTrainingSlot: APIProgramSlot?
}

// MARK: - Exercise library

/// `GET /v1/exercises` → `{ items, next_cursor }`. Used to build an id → name
/// lookup so programmed exercises (which carry only `exercise_id`) can render a
/// human label/muscle in the Phase-1 views.
struct APIExerciseList: Codable, Sendable {
    let items: [APIExercise]
    let nextCursor: String?
}

/// A row in the exercise library. Only the fields the Programs views need.
struct APIExercise: Codable, Sendable, Identifiable {
    let id: String
    let name: String
    let primaryMuscle: String?
}

// MARK: - Templates

/// `GET /v1/program-templates` → `{ items: [APITemplateSummary] }`.
struct APITemplateList: Codable, Sendable {
    let items: [APITemplateSummary]
    let nextCursor: String?
}

/// A curated or shared template. `ownerId`/`visibility` are null for curated.
struct APITemplateSummary: Codable, Sendable, Identifiable {
    let id: String
    let slug: String
    let name: String
    let description: String?
    let author: String?
    let goal: String?
    let microcycleLength: Int
    let mesocycleLengthMicrocycles: Int
    let ownerId: String?
    let visibility: String?
}

// MARK: - Body metrics (Health → Metrics)

/// `GET /v1/body-metrics` → `{ items: [BodyMetricResponse] }` (newest-first).
struct APIBodyMetricList: Codable, Sendable {
    let items: [APIBodyMetric]
}

/// One logged body-composition reading. Decimal fields arrive as JSON *strings*
/// (e.g. `weight_kg: "81.90"`) — convenience accessors parse them to `Double`.
/// Mirrors `BodyMetricResponse` (id/recorded_at/weight_kg/body_fat_pct/created_at
/// required; the rest nullable).
struct APIBodyMetric: Codable, Sendable, Identifiable {
    let id: String
    let recordedAt: String
    let weightKg: String?
    let bodyFatPct: String?
    let neckCm: String?
    let waistCm: String?
    let hipCm: String?
    let createdAt: String

    var weightKgValue: Double? { weightKg.flatMap(Double.init) }
    var bodyFatPctValue: Double? { bodyFatPct.flatMap(Double.init) }
}

/// `POST /v1/body-metrics` body (`BodyMetricCreate`). We only send weight from
/// iOS; `recordedAt` is an ISO-8601 instant. Decimals go over the wire as strings.
struct APIBodyMetricCreate: Encodable, Sendable {
    let weightKg: String
    let recordedAt: String
}

// MARK: - Readiness / Wearable history

/// `GET /v1/readiness/history?from=&to=` → `{ items: [ReadinessDay] }`.
struct APIReadinessHistory: Codable, Sendable {
    let items: [APIReadinessDay]
}

/// One day of synced wearable + readiness data. `date` is `YYYY-MM-DD`; `hrvMs`
/// is a decimal-as-string. All metrics are nullable (a day may be partial).
struct APIReadinessDay: Codable, Sendable, Identifiable {
    let date: String
    let score: Int?
    let band: String?
    let hrvMs: String?
    let restingHr: Int?
    let sleepMinutes: Int?
    let steps: Int?

    var id: String { date }
    var hrvMsValue: Double? { hrvMs.flatMap(Double.init) }
}

// MARK: - Wearable connection (Fitbit via Google Health)

/// `GET /v1/integrations/health/status` → `HealthStatusResponse`. The wearable
/// connection the Health page reads (Settings defers to it).
struct APIHealthStatus: Codable, Sendable {
    let connected: Bool
    let needsReauth: Bool
    let lastSyncedAt: String?
    let lastSyncedActivityAt: String?
    let scopes: [String]
}

// MARK: - Today: readiness (today)

/// `GET /v1/readiness/today` → `ReadinessTodayResponse`. `score`/`band` are null
/// when the wearable has no data for today (`hasData == false`) — the Today
/// readiness tile falls back to a "Connect a wearable" state.
struct APIReadinessToday: Codable, Sendable {
    let date: String
    let score: Int?
    let band: String?
    let hasData: Bool
}

// MARK: - Today: nutrition (day summary + targets)

/// `GET /v1/nutrition/day?date=` → `DaySummaryResponse`. Today reads only the
/// totals; the Nutrition log-first day also reads `perMeal` (the logged meals +
/// their items), `adherence`, and `trackingMode`. `perMeal`/`adherence`/
/// `trackingMode` are decoded with defaults so the Today decode path is unaffected.
struct APIDaySummary: Codable, Sendable {
    let date: String
    let totals: APIDayMacros
    let perMeal: [APIDayPerMeal]
    let adherence: APIDayAdherence?
    let trackingMode: String?

    enum CodingKeys: String, CodingKey {
        case date, totals, perMeal, adherence, trackingMode
    }

    init(from decoder: any Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        date = try c.decode(String.self, forKey: .date)
        totals = try c.decode(APIDayMacros.self, forKey: .totals)
        perMeal = try c.decodeIfPresent([APIDayPerMeal].self, forKey: .perMeal) ?? []
        adherence = try c.decodeIfPresent(APIDayAdherence.self, forKey: .adherence)
        trackingMode = try c.decodeIfPresent(String.self, forKey: .trackingMode)
    }

    /// Memberwise init kept for the preview/offline seed in `TodayStore`.
    init(
        date: String,
        totals: APIDayMacros,
        perMeal: [APIDayPerMeal] = [],
        adherence: APIDayAdherence? = nil,
        trackingMode: String? = nil
    ) {
        self.date = date
        self.totals = totals
        self.perMeal = perMeal
        self.adherence = adherence
        self.trackingMode = trackingMode
    }
}

/// `DayMacros` — every macro arrives as a decimal *string* (e.g. `"1620.00"`).
struct APIDayMacros: Codable, Sendable {
    let kcal: String
    let proteinG: String
    let carbsG: String
    let fatG: String
    let fiberG: String?
}

/// `DayPerMeal` — one logged meal in the day summary, with its denormalized
/// totals and the items it contains. `eatenAt` is an ISO-8601 instant; `mealType`
/// is a `MealType` slug. This is the day screen's source of truth (no separate
/// `/meals` range fetch needed).
struct APIDayPerMeal: Codable, Sendable, Identifiable {
    let mealId: String
    let mealType: String
    let eatenAt: String
    let totals: APIDayMacros
    let items: [APIMealItem]

    var id: String { mealId }
}

/// `MealItemResponse` — a logged item. Macros are denormalized decimal *strings*;
/// `amount`/`grams` likewise. `foodId` references the food (name resolved
/// separately by the store). `unit` is `g`/`ml`/`serving`.
struct APIMealItem: Codable, Sendable, Identifiable {
    let id: String
    let mealId: String
    let foodId: String
    let amount: String?
    let unit: String
    let servingId: String?
    let grams: String
    let kcal: String?
    let proteinG: String?
    let carbsG: String?
    let fatG: String?
    let fiberG: String?
    let createdAt: String?
}

/// `DayAdherence` — plan-mode progress (planned vs completed meals). Null in
/// flexible mode.
struct APIDayAdherence: Codable, Sendable {
    let plannedMeals: Int
    let completedMeals: Int
    let completedPlanMealIds: [String]
}

// MARK: - Nutrition: food search / recent

/// `GET /v1/foods/search?q=` → `FoodList` (`{ items, next_cursor }`). Cursor
/// pagination; the Add-food sheet reads the first page only.
struct APIFoodList: Codable, Sendable {
    let items: [APIFood]
    let nextCursor: String?
}

/// `FoodResponse` — a food in the library (USDA / OFF / custom / user). Per-100g
/// macros + serving fields arrive as decimal *strings* (nullable). `servings` is
/// the list of named servings (default `[]`). The Add-food sheet renders
/// name/brand + kcal/100g and logs `amount`+`unit`.
struct APIFood: Codable, Sendable, Identifiable {
    let id: String
    let source: String
    let name: String
    let brand: String?
    let servingSizeG: String?
    let servingLabel: String?
    // Wire keys are snake_case (`kcal_per_100g`, …); `convertFromSnakeCase`
    // maps them to these camelCase names (the segment after `per_` is `100g`,
    // whose leading digit is unchanged → `…Per100g`).
    let kcalPer100g: String?
    let proteinGPer100g: String?
    let carbsGPer100g: String?
    let fatGPer100g: String?
    let fiberGPer100g: String?
    let servings: [APIFoodServing]?
}

/// `FoodServingResponse` — a named serving with its resolved gram weight. The
/// client logs a serving as `amount` (count) + `unit: "serving"` + `serving_id`.
struct APIFoodServing: Codable, Sendable, Identifiable {
    let id: String
    let description: String
    let grams: String?
    let isDefault: Bool
}

/// `GET /v1/foods/recent` → `RecentFoodList`. Each row carries enough to render a
/// one-tap "recent chip" (name + last kcal) and re-log the food in one tap via
/// `last_amount`/`last_unit`/`last_serving_id`.
struct APIRecentFoodList: Codable, Sendable {
    let items: [APIRecentFood]
}

/// `RecentFoodResponse` — a previously-logged food. Decimals are strings.
struct APIRecentFood: Codable, Sendable, Identifiable {
    let foodId: String
    let name: String
    let brand: String?
    let source: String
    let lastAmount: String?
    let lastUnit: String
    let lastServingId: String?
    let lastGrams: String
    let lastKcal: String?
    let lastProteinG: String?

    var id: String { foodId }
}

// MARK: - Nutrition: meals (logging)

/// `MealResponse` — a logged meal (flexible or plan-seeded). `sourcePlanMealId`
/// is set when the meal materializes a plan slot. Used to resolve food names for
/// the day rows and to land logged items.
struct APIMeal: Codable, Sendable, Identifiable {
    let id: String
    let eatenAt: String
    let mealType: String
    let name: String?
    let notes: String?
    let items: [APIMealItem]
    let sourcePlanMealId: String?
    let sourcePlanDate: String?
    let createdAt: String?
}

/// `MealCreate` body — POST `/v1/meals`. `eatenAt` is an ISO-8601 instant;
/// `mealType` defaults to `snack` (no surfaced meal type in the log-first UI).
struct APIMealCreate: Encodable, Sendable {
    let eatenAt: String
    let mealType: String
    let name: String?
}

/// `MealItemCreate` body — POST `/v1/meals/{id}/items`. Pass `amount` + `unit`
/// (g/ml/serving) with an optional `servingId`; the server resolves grams and
/// denormalizes macros from the food's per-100g values.
struct APIMealItemCreate: Encodable, Sendable {
    let foodId: String
    let amount: Double
    let unit: String
    let servingId: String?
}

/// `GET /v1/nutrition/targets` → `MealPlanTargets`. Decimal-as-string targets.
/// 409s when the profile lacks height/birthdate/weight, so the store fetches it
/// best-effort and renders "set up your plan" when absent.
struct APIMealPlanTargets: Codable, Sendable {
    let targetKcal: String
    let targetProteinG: String
    let targetCarbsG: String
    let targetFatG: String
}

// MARK: - Today: insights feed

/// `GET /v1/insights` → `{ items, next_cursor }`. The command center reads the
/// top 1–3 active cards (read-only; apply/dismiss lives on the Insights surface).
struct APIInsightList: Codable, Sendable {
    let items: [APIInsight]
    let nextCursor: String?
}

/// One analytics insight (`InsightResponse`). `kind` is an
/// `AnalyticsInsightKind`; `severity` an `AnalyticsInsightSeverity`. `body`/
/// `rationale`/`subject` are nullable. `payload` is omitted (untyped object).
struct APIInsight: Codable, Sendable, Identifiable {
    let id: String
    let kind: String
    let severity: String
    let title: String
    let body: String?
    let rationale: String?
    let subject: String?
    let surfacedAt: String?
    let dismissedAt: String?

    /// The display copy: the rationale (LLM-written) when present, else the body.
    var displayBody: String? { rationale ?? body }
}

// MARK: - Workout session (start / detail)

/// `POST /v1/programs/{id}/start-session`, `GET /v1/workout-sessions/{id}`,
/// `POST .../finish`, `POST .../skip` → `WorkoutSessionResponse`. The Today card
/// only needs the id; the Workouts active surface reads `workoutExercises`/sets.
/// `bodyweightKg` is a decimal-as-string (nullable); `workoutExercises` defaults
/// to `[]` so the Today decode path (which never reads it) is unaffected.
struct APIWorkoutSession: Codable, Sendable, Identifiable {
    let id: String
    let name: String?
    let scheduledWorkoutId: String?
    let startedAt: String?
    let endedAt: String?
    let notes: String?
    let bodyweightKg: String?
    let perceivedExertion: Int?
    let workoutExercises: [APIWorkoutExercise]

    enum CodingKeys: String, CodingKey {
        case id, name, scheduledWorkoutId, startedAt, endedAt, notes, bodyweightKg, perceivedExertion, workoutExercises
    }

    init(from decoder: any Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        id = try c.decode(String.self, forKey: .id)
        name = try c.decodeIfPresent(String.self, forKey: .name)
        scheduledWorkoutId = try c.decodeIfPresent(String.self, forKey: .scheduledWorkoutId)
        startedAt = try c.decodeIfPresent(String.self, forKey: .startedAt)
        endedAt = try c.decodeIfPresent(String.self, forKey: .endedAt)
        notes = try c.decodeIfPresent(String.self, forKey: .notes)
        bodyweightKg = try c.decodeIfPresent(String.self, forKey: .bodyweightKg)
        perceivedExertion = try c.decodeIfPresent(Int.self, forKey: .perceivedExertion)
        workoutExercises = try c.decodeIfPresent([APIWorkoutExercise].self, forKey: .workoutExercises) ?? []
    }
}

/// `GET /v1/workout-sessions` → `WorkoutSessionList` (`{ items, next_cursor }`).
/// Cursor pagination; the history list reads the first page.
struct APIWorkoutSessionList: Codable, Sendable {
    let items: [APIWorkoutSessionListItem]
    let nextCursor: String?
}

/// A row in the session history (`WorkoutSessionListItem`). Lighter than the full
/// session — no `workoutExercises`. `bodyweightKg` is a decimal-as-string.
struct APIWorkoutSessionListItem: Codable, Sendable, Identifiable {
    let id: String
    let name: String?
    let startedAt: String
    let endedAt: String?
    let perceivedExertion: Int?
    let bodyweightKg: String?
}

/// `WorkoutExerciseResponse` — one exercise in a session, with its logged sets.
/// `exerciseId` references the library (name resolved by the store).
/// `blockKind` is `warmup`/`working`/`cooldown`; `substitutedForExerciseId`
/// is set when this exercise stands in for a programmed one (one-session swap).
struct APIWorkoutExercise: Codable, Sendable, Identifiable {
    let id: String
    let exerciseId: String
    let position: Int
    let notes: String?
    let blockKind: String
    let blockLabel: String?
    let substitutedForExerciseId: String?
    let sets: [APIWorkoutSet]
}

/// `SetResponse` — one logged set. `weightKg`/`rpe`/`distanceMeters` arrive as
/// decimal *strings* (nullable); convenience accessors parse them. `setType` is a
/// `SetType` slug (`working`/`warmup`/`drop`/…). Structured-work fields
/// (`rounds`/`segments`) are decoded but the core loop renders weight/reps/rpe.
struct APIWorkoutSet: Codable, Sendable, Identifiable {
    let id: String
    let setIndex: Int
    let setType: String
    let weightKg: String?
    let reps: Int?
    let durationSeconds: Int?
    let distanceMeters: String?
    let rpe: String?
    let rir: Int?
    let isPr: Bool
    let notes: String?
    let rounds: Int?

    enum CodingKeys: String, CodingKey {
        case id, setIndex, setType, weightKg, reps, durationSeconds, distanceMeters, rpe, rir, isPr, notes, rounds
    }

    var weightKgValue: Double? { weightKg.flatMap(Double.init) }
    var rpeValue: Double? { rpe.flatMap(Double.init) }
}

/// `SetCreate` body — POST `/v1/workout-exercises/{id}/sets`. Decimals (weight,
/// rpe) go over the wire as JSON *strings* to match the server's `Decimal`
/// columns. `setType` defaults to `working`; `setIndex` nil lets the server
/// append.
struct APISetCreate: Encodable, Sendable {
    let weightKg: String?
    let reps: Int?
    let rpe: String?
    let rir: Int?
    let setType: String
}

/// `SetUpdate` body — PATCH `/v1/sets/{id}`. All optional; only the edited fields
/// are sent. Decimals as strings.
struct APISetUpdate: Encodable, Sendable {
    let weightKg: String?
    let reps: Int?
    let rpe: String?
}

/// `POST /v1/workout-sessions/{id}/exercises` body. Append an exercise to the
/// in-progress session (used when starting a freestyle session from a slot the
/// server couldn't resolve, or adding ad-hoc work).
struct APIAddExercise: Encodable, Sendable {
    let exerciseId: String
    let position: Int?
}

// MARK: - Error envelope

/// The single API error shape from api-conventions.md:
/// `{ "error": { "code", "message", "details" } }`.
struct APIErrorEnvelope: Codable, Sendable {
    struct Body: Codable, Sendable {
        let code: String
        let message: String
    }
    let error: Body
}
