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

/// `GET /v1/nutrition/day?date=` → `DaySummaryResponse`. Only the totals are
/// read on Today; `per_meal`/`adherence`/`tracking_mode` belong to Nutrition.
struct APIDaySummary: Codable, Sendable {
    let date: String
    let totals: APIDayMacros
}

/// `DayMacros` — every macro arrives as a decimal *string* (e.g. `"1620.00"`).
struct APIDayMacros: Codable, Sendable {
    let kcal: String
    let proteinG: String
    let carbsG: String
    let fatG: String
    let fiberG: String?
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

// MARK: - Workout session (start)

/// `POST /v1/programs/{id}/start-session` → `WorkoutSessionResponse`. The Today
/// card only needs the id to navigate into the in-progress session.
struct APIWorkoutSession: Codable, Sendable, Identifiable {
    let id: String
    let name: String?
    let startedAt: String?
    let endedAt: String?
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
