//
//  MockData.swift
//  GymApp
//
//  Static mock content for the visual pass — the same fake user across every
//  screen: Alex Chen, week 4/8 of "PPL — Vanilla 6-day". Mirrors
//  tasks/ios/assets/data.js. Networking/persistence is out of scope.
//

import SwiftUI

enum MockData {
    // MARK: User / program

    static let userName = "Alex Chen"
    static let userInitials = "AC"
    static let userEmail = "alex@chen.fyi"
    static let todayLong = "Tuesday, 27 May"
    /// Editorial day kicker for the nutrition masthead.
    static let todayKicker = "Tuesday · May 27"
    static let appVersion = "v0.32.1"

    // MARK: Today — Fitbit metric carousel

    struct HealthMetric: Identifiable {
        let id = UUID()
        let label: String
        let value: String
        var unit: String? = nil
        let sub: String
        let systemImage: String
        var ringValue: Double? = nil
    }

    static let healthMetrics: [HealthMetric] = [
        .init(label: "Readiness", value: "78", sub: "High · push it", systemImage: "heart.fill", ringValue: 0.78),
        .init(label: "Sleep", value: "7h 24m", sub: "↑ 22 min", systemImage: "moon.fill"),
        .init(label: "Resting HR", value: "56", unit: "bpm", sub: "↓ 2", systemImage: "heart"),
        .init(label: "HRV", value: "64", unit: "ms", sub: "↑ 8 ms", systemImage: "bolt.heart"),
        .init(label: "Steps", value: "4,287", sub: "43% of goal", systemImage: "figure.walk", ringValue: 0.43),
        .init(label: "Active min", value: "32 / 60", sub: "↑ 8", systemImage: "timer"),
        .init(label: "Calories", value: "2,140", unit: "kcal", sub: "1,720 BMR", systemImage: "flame.fill"),
        .init(label: "SpO₂", value: "97", unit: "%", sub: "Normal", systemImage: "drop.fill"),
    ]

    // MARK: Today — recommendation

    struct Recommendation {
        let kicker: String
        let title: String
        let rationale: String
        let confidence: String
        let cta: String
    }

    static let topRecommendation = Recommendation(
        kicker: "Add weight",
        title: "Try 95 kg on bench",
        rationale: "8 / 8 / 7 reps @ RPE 7.5–9 last session. Top of range.",
        confidence: "High confidence",
        cta: "Apply"
    )

    // MARK: Scheduled workout

    struct ScheduledWorkout {
        let kicker: String
        let headline: String
        let day: String
        let exercises: Int
        let minutes: Int
        let sets: Int
    }

    static let scheduledToday = ScheduledWorkout(
        kicker: "Today — Push A · Week 4",
        headline: "Bench, press & pump",
        day: "Push A",
        exercises: 5,
        minutes: 58,
        sets: 21
    )

    // MARK: Week strip

    struct WeekDay: Identifiable {
        let id = UUID()
        let dow: String
        let date: Int
        let tag: String
        var done = false
        var today = false
        var rest = false
    }

    static let weekStrip: [WeekDay] = [
        .init(dow: "M", date: 26, tag: "Legs", done: true),
        .init(dow: "T", date: 27, tag: "Push", today: true),
        .init(dow: "W", date: 28, tag: "Pull"),
        .init(dow: "T", date: 29, tag: "Rest", rest: true),
        .init(dow: "F", date: 30, tag: "Push"),
        .init(dow: "S", date: 31, tag: "Legs"),
        .init(dow: "S", date: 1, tag: "Rest", rest: true),
    ]

    // MARK: Recent sessions

    struct Session: Identifiable {
        let id = UUID()
        let date: String
        let day: String
        let duration: String
        let sets: Int
        let volume: String
        var prs: Int = 0
    }

    static let recentSessions: [Session] = [
        .init(date: "Mon 26", day: "Legs A", duration: "1:08", sets: 22, volume: "6,480 kg", prs: 1),
        .init(date: "Sat 24", day: "Pull A", duration: "0:55", sets: 19, volume: "4,220 kg"),
        .init(date: "Fri 23", day: "Push A", duration: "0:58", sets: 21, volume: "5,125 kg", prs: 2),
        .init(date: "Wed 21", day: "Legs B", duration: "1:12", sets: 24, volume: "6,740 kg"),
        .init(date: "Tue 20", day: "Pull B", duration: "0:54", sets: 20, volume: "4,380 kg", prs: 1),
    ]

    // MARK: Nutrition

    static let kcalConsumed = 1_620
    static let kcalTarget = 2_680
    static let kcalRemaining = 1_060

    struct Macro: Identifiable {
        let id = UUID()
        let label: String
        let value: String
        let target: String
        let fraction: Double
        let tone: Color
    }

    static let macros: [Macro] = [
        .init(label: "Protein", value: "134g", target: "/ 200", fraction: 0.67, tone: .accent),
        .init(label: "Carbs", value: "168g", target: "/ 300", fraction: 0.56, tone: .warning),
        .init(label: "Fat", value: "51g", target: "/ 80", fraction: 0.64, tone: .success),
    ]

    /// The day's P/C/F as consumed/target grams — drives the Direction A macro
    /// strip (carbs & fat first-class alongside protein).
    struct MacroLine: Identifiable {
        let id = UUID()
        let label: String
        let value: Int
        let target: Int
    }

    static let macroLines: [MacroLine] = [
        .init(label: "Protein", value: 134, target: 200),
        .init(label: "Carbs", value: 168, target: 300),
        .init(label: "Fat", value: 51, target: 80),
    ]

    enum FoodSource { case usda, barcode, manual, favorite
        var systemImage: String {
            switch self {
            case .usda:     return "list.bullet"
            case .barcode:  return "barcode"
            case .manual:   return "pencil"
            case .favorite: return "star.fill"
            }
        }
    }

    struct FoodItem: Identifiable {
        let id = UUID()
        let name: String
        let kcal: Int
        let source: FoodSource
    }

    struct Meal: Identifiable {
        let id = UUID()
        /// User-typed name, or nil → render "Meal {index+1}".
        var name: String? = nil
        let at: String
        let kcal: Int
        let protein: Int
        let carbs: Int
        let fat: Int
        let items: [FoodItem]
    }

    static let meals: [Meal] = [
        .init(name: "Pre-workout", at: "07:30", kcal: 490, protein: 36, carbs: 58, fat: 12, items: [
            .init(name: "Oats, rolled", kcal: 304, source: .favorite),
            .init(name: "Whey isolate", kcal: 117, source: .barcode),
            .init(name: "Blueberries", kcal: 69, source: .favorite),
        ]),
        .init(name: "Post-workout", at: "12:45", kcal: 760, protein: 58, carbs: 74, fat: 24, items: [
            .init(name: "Chicken thigh", kcal: 410, source: .usda),
            .init(name: "Jasmine rice", kcal: 234, source: .favorite),
            .init(name: "Greens + olive oil", kcal: 116, source: .manual),
        ]),
        .init(at: "15:10", kcal: 176, protein: 17, carbs: 24, fat: 4, items: [
            .init(name: "Greek yogurt", kcal: 130, source: .barcode),
            .init(name: "Honey", kcal: 46, source: .manual),
        ]),
        .init(name: "Dinner", at: "—", kcal: 0, protein: 0, carbs: 0, fat: 0, items: []),
    ]

    // MARK: Insights

    struct WeekStat: Identifiable {
        let id = UUID()
        let label: String
        let value: String
        var unit: String? = nil
        let delta: StatDelta
    }

    static let insightStats: [WeekStat] = [
        .init(label: "Sessions / wk", value: "5.2", delta: .up("↑ 0.8")),
        .init(label: "Sets / wk", value: "96", delta: .up("↑ 11")),
        .init(label: "Tonnage / wk", value: "23,180", unit: "kg", delta: .up("↑ 6%")),
        .init(label: "PRs · block", value: "7", delta: .up("↑ 3")),
    ]

    static let thisWeekStats: [WeekStat] = [
        .init(label: "Sessions", value: "5/6", delta: .up("↑ on pace")),
        .init(label: "Sets", value: "96", delta: .up("↑ 11")),
        .init(label: "Tonnage", value: "23k", unit: "kg", delta: .up("↑ 6%")),
    ]

    /// Per-muscle working sets vs target, in the prototype's display order.
    struct MuscleVolume: Identifiable {
        let id = UUID()
        let name: String
        let sets: Int
        let target: Int
        /// 0...4 heat level.
        var level: Int {
            guard target > 0, sets > 0 else { return sets > 0 ? 1 : 0 }
            let r = Double(sets) / Double(target)
            if r >= 1.2 { return 4 }
            if r >= 0.9 { return 3 }
            if r >= 0.6 { return 2 }
            return 1
        }
    }

    static let muscleVolumes: [MuscleVolume] = [
        .init(name: "chest", sets: 14, target: 14),
        .init(name: "front delts", sets: 11, target: 9),
        .init(name: "side delts", sets: 9, target: 9),
        .init(name: "rear delts", sets: 5, target: 9),
        .init(name: "traps", sets: 6, target: 8),
        .init(name: "mid back", sets: 8, target: 10),
        .init(name: "lats", sets: 16, target: 16),
        .init(name: "lower back", sets: 4, target: 6),
        .init(name: "biceps", sets: 12, target: 12),
        .init(name: "triceps", sets: 13, target: 12),
        .init(name: "forearms", sets: 2, target: 4),
        .init(name: "abs", sets: 6, target: 8),
        .init(name: "obliques", sets: 2, target: 4),
        .init(name: "glutes", sets: 14, target: 14),
        .init(name: "quads", sets: 18, target: 16),
        .init(name: "hamstrings", sets: 10, target: 12),
        .init(name: "adductors", sets: 0, target: 4),
        .init(name: "abductors", sets: 0, target: 4),
        .init(name: "calves", sets: 6, target: 8),
    ]

    struct TonnagePoint: Identifiable {
        let id = UUID()
        let week: Int
        let kg: Double
    }

    static let tonnageTrend: [TonnagePoint] = [
        .init(week: 1, kg: 18_900),
        .init(week: 2, kg: 19_600),
        .init(week: 3, kg: 20_400),
        .init(week: 4, kg: 20_900),
        .init(week: 5, kg: 21_500),
        .init(week: 6, kg: 22_100),
        .init(week: 7, kg: 22_700),
        .init(week: 8, kg: 23_180),
    ]

    struct InsightCard: Identifiable {
        let id = UUID()
        let kind: String
        let title: String
        let body: String
        let tone: Color
    }

    static let insightCards: [InsightCard] = [
        .init(kind: "PR streak", title: "Three PRs this week",
              body: "Bench, OHP, Bulgarian split squat all moved up.", tone: .success),
        .init(kind: "Plateau", title: "Pull-ups stuck at 9 reps",
              body: "Three sessions. Try a BW deload or rest-pause.", tone: .accent),
        .init(kind: "Under recovered", title: "Sleep dipped this week",
              body: "Average 6.4h vs 7.5h baseline.", tone: .warning),
    ]

    // MARK: Active workout session

    struct WorkoutSet: Identifiable {
        let id = UUID()
        let index: Int
        let weight: String
        var reps: String = ""
        var rpe: String = ""
        var previous: String = "92.5 × 8"
        var done = false
        var current = false
    }

    struct ActiveExercise: Identifiable {
        let id = UUID()
        let name: String
        let shortName: String
        let target: String
        let restSec: Int
        var doneSets: Int
        var totalSets: Int
        var active = false
    }

    struct ActiveSession {
        let kicker = "Push A · Week 4"
        let elapsed = "14:32"
        let position = "Exercise 1 of 5"
        let setsComplete = "5 of 17 sets complete"
        let exercises: [ActiveExercise]
        let activeExerciseName = "Barbell Bench Press"
        let activeExerciseTarget = "4 × 6–8 @ RPE 8 · rest 3:00"
        let activeWeight = "92.5 kg · ea 36.25"
        /// Plate stack on one side (kg), outer → inner.
        let plates: [Double] = [20, 20, 5]
        let sets: [WorkoutSet]
        // Rest bar
        let restElapsed = "1:43"
        let restTotal = "3:00"
        let restFraction = 0.42
    }

    static let activeSession = ActiveSession(
        exercises: [
            .init(name: "Bench Press", shortName: "Bench Press", target: "", restSec: 180,
                  doneSets: 2, totalSets: 4, active: true),
            .init(name: "Overhead Press", shortName: "OHP", target: "", restSec: 150,
                  doneSets: 0, totalSets: 4),
            .init(name: "Incline DB Press", shortName: "Incline DB", target: "", restSec: 120,
                  doneSets: 0, totalSets: 3),
            .init(name: "Cable Lateral Raise", shortName: "Lateral", target: "", restSec: 90,
                  doneSets: 0, totalSets: 3),
            .init(name: "Triceps Pushdown", shortName: "Pushdown", target: "", restSec: 75,
                  doneSets: 0, totalSets: 3),
        ],
        sets: [
            .init(index: 1, weight: "92.5", reps: "8", rpe: "7.5", done: true),
            .init(index: 2, weight: "92.5", reps: "8", rpe: "8", done: true),
            .init(index: 3, weight: "92.5", previous: "92.5 × 7", current: true),
            .init(index: 4, weight: "92.5"),
        ]
    )

    // MARK: Exercise detail

    struct ExerciseStat: Identifiable {
        let id = UUID()
        let label: String
        let value: String
        var unit: String? = nil
        let delta: StatDelta
    }

    struct ExerciseDetail {
        let kicker = "Compound · barbell"
        let name = "Barbell Bench Press"
        let muscles: [(String, Bool)] = [("Chest", true), ("Triceps", false), ("Front delts", false)]
        let stats: [ExerciseStat] = [
            .init(label: "e1RM", value: "120.4", unit: "kg", delta: .up("+1.9 kg · PR")),
            .init(label: "Best set", value: "95 × 8", delta: .neutral("May 23")),
            .init(label: "All-time", value: "100 × 5", delta: .neutral("Apr 11")),
            .init(label: "Volume / wk", value: "2,940", unit: "kg", delta: .up("↑ 8%")),
        ]
        let recTitle = "Try 97.5 kg next session"
        let recBody = "Double-progression rule fired — every working set hit top of range at RPE ≤ 9."
        let e1rmCurrent = "120.4"
        let e1rmDelta = "↑ 14.2 kg vs Dec"
        let e1rmTrend: [E1RMPoint]
        let volumeBars: [VolumeBar]
    }

    struct E1RMPoint: Identifiable {
        let id = UUID()
        let month: String
        let value: Double
        var isCurrent = false
    }

    struct VolumeBar: Identifiable {
        let id = UUID()
        let session: Int
        let value: Double
        var isPR = false
    }

    static let exerciseDetail = ExerciseDetail(
        e1rmTrend: [
            .init(month: "Dec", value: 106.2),
            .init(month: "Jan", value: 109.0),
            .init(month: "Feb", value: 112.1),
            .init(month: "Mar", value: 114.8),
            .init(month: "Apr", value: 117.5),
            .init(month: "May", value: 120.4, isCurrent: true),
        ],
        volumeBars: (1...11).map { i in
            VolumeBar(session: i, value: Double(24 + i * 7), isPR: i == 11)
        }
    )

    // MARK: Session summary

    struct SummaryStat: Identifiable {
        let id = UUID()
        let label: String
        let value: String
        var unit: String? = nil
        var delta: StatDelta? = nil
    }

    struct SummaryMuscle: Identifiable {
        let id = UUID()
        let name: String
        let sets: Int
        let target: Int
        let fraction: Double
        var short = false
    }

    struct SummaryExercise: Identifiable {
        let id = UUID()
        let name: String
        let sets: String
    }

    struct SummaryRec: Identifiable {
        let id = UUID()
        let systemImage: String
        let title: String
        let detail: String
    }

    struct SessionSummary {
        let prKicker = "2 personal records"
        let headline = "Bench & OHP up"
        let prDetail = "Bench 95 × 8 · e1RM 120.4 kg (+1.9)"
        let stats: [SummaryStat] = [
            .init(label: "Duration", value: "58", unit: "min"),
            .init(label: "Sets", value: "21"),
            .init(label: "Tonnage", value: "5,125", unit: "kg", delta: .up("↑ 240 vs avg")),
            .init(label: "Avg RPE", value: "8.2", delta: .neutral("On target")),
        ]
        let muscles: [SummaryMuscle] = [
            .init(name: "Chest", sets: 9, target: 7, fraction: 1.0),
            .init(name: "Front delts", sets: 7, target: 6, fraction: 0.88),
            .init(name: "Side delts", sets: 3, target: 4, fraction: 0.60, short: true),
            .init(name: "Triceps", sets: 6, target: 6, fraction: 0.75),
        ]
        let exercises: [SummaryExercise] = [
            .init(name: "Bench Press", sets: "95 × 8 PR · 92.5 × 8 · 92.5 × 7 · 85 × 9"),
            .init(name: "Overhead Press", sets: "57.5 × 9 PR · 55 × 9 · 55 × 8"),
            .init(name: "Incline DB Press", sets: "32 × 12 · 32 × 11 · 32 × 10"),
        ]
        let recs: [SummaryRec] = [
            .init(systemImage: "arrow.right", title: "Bench → 97.5 kg", detail: "+ progression"),
            .init(systemImage: "equal", title: "OHP → hold 57.5", detail: "repeat top"),
            .init(systemImage: "plus", title: "Side delts +1 set", detail: "below target"),
        ]
    }

    static let sessionSummary = SessionSummary()

    // MARK: Programs

    /// Program-level intensity scale — one choice for the whole program.
    enum IntensityMode: String, CaseIterable, Identifiable, Sendable {
        case rpe, rir, off
        var id: String { rawValue }
        /// Segment label.
        var title: String {
            switch self {
            case .rpe: return "RPE"
            case .rir: return "RIR"
            case .off: return "Off"
            }
        }
        /// Per-exercise target field label, e.g. "RPE target".
        var targetLabel: String { "\(title) target" }
    }

    /// How an exercise's reps are expressed.
    enum RepMode: String, CaseIterable, Identifiable, Sendable {
        case range, target
        var id: String { rawValue }
        var title: String { self == .range ? "Range" : "Target" }
    }

    struct ProgramExercise: Identifiable {
        let id = UUID()
        var name: String
        var muscle: String
        var sets: Int
        /// Rep value — a span ("6–8") in range mode or a single number ("12").
        var reps: String
        var repMode: RepMode = .range
        /// Intensity value interpreted via the program's `intensityMode`
        /// (e.g. "8" for RPE, "1–2" for RIR). Ignored when mode is `.off`.
        var intensityTarget: String = "8"
    }

    /// A single slot in a program's microcycle. A slot is either a training day
    /// (with exercises) or an explicit rest slot. `slotIndex` is its 0-based
    /// position in the microcycle rotation.
    struct ProgramDay: Identifiable {
        let id = UUID()
        var slotIndex: Int = 0
        var isRestDay: Bool = false
        var name: String
        /// Muscle-group summary line, e.g. "Chest · delts · triceps".
        var muscleSummary: String = ""
        var exercises: [ProgramExercise]
    }

    struct Program: Identifiable {
        let id = UUID()
        var name: String
        var goal: String
        var progressionStrategy: String = "Double progression"
        var intensityMode: IntensityMode = .rpe
        /// Number of slots in one microcycle (= `days.count`, rest slots included).
        var microcycleLength: Int
        /// Microcycles per mesocycle, deload excluded.
        var mesocycleLengthMicrocycles: Int = 4
        /// Whether the program auto-inserts a deload microcycle after the block.
        var autoDeload: Bool = true
        // Mock rotation position.
        /// Current slot within the microcycle (0-based).
        var currentSlotIndex: Int = 0
        /// Which microcycle repetition we're in (1-based).
        var currentRepetition: Int = 1
        /// Whether the program is currently in its deload microcycle.
        var inDeload: Bool = false
        var active = false
        var days: [ProgramDay] = []
    }

    /// Template gallery categories.
    enum TemplateCategory: String, CaseIterable, Identifiable, Sendable {
        case hypertrophy = "Hypertrophy"
        case strength = "Strength"
        case endurance = "Endurance"
        case general = "General"
        var id: String { rawValue }
    }

    /// Who can see a template — drives the browse grouping.
    enum TemplateVisibility: String, CaseIterable, Identifiable, Sendable {
        case curated = "Curated"
        case `private` = "Private"
        case shared = "Shared"
        var id: String { rawValue }
        var title: String { rawValue }
    }

    struct ProgramTemplate: Identifiable {
        let id = UUID()
        let name: String
        let category: TemplateCategory
        let description: String
        let goal: String
        /// Slots per microcycle (rest slots included).
        let microcycleLength: Int
        /// Microcycles per mesocycle, deload excluded.
        let mesocycleLengthMicrocycles: Int
        var visibility: TemplateVisibility = .curated
        /// True for templates the user saved themselves.
        var ownerIsMe: Bool = false
        var rating: String = "4.8"
        var active = false
        var days: [ProgramDay] = []
    }

    // MARK: Renders a scheme line from structured fields.

    /// "4 × 6–8 · RPE 8" — sets × reps, plus the intensity target when the
    /// program's mode isn't Off.
    static func schemeLine(_ ex: ProgramExercise, mode: IntensityMode) -> String {
        var s = "\(ex.sets) × \(ex.reps)"
        if mode != .off {
            s += " · \(mode.title) \(ex.intensityTarget)"
        }
        return s
    }

    /// Builds an explicit rest slot at the given index.
    private static func restSlot(_ index: Int) -> ProgramDay {
        .init(slotIndex: index, isRestDay: true, name: "Rest", muscleSummary: "", exercises: [])
    }

    /// The active program's microcycle — eight slots: a PPL pair separated by
    /// explicit rest slots (Push/Pull/Legs/Rest/Push/Pull/Legs/Rest).
    static let pplDays: [ProgramDay] = [
        .init(slotIndex: 0, name: "Push A", muscleSummary: "Chest · delts · triceps", exercises: [
            .init(name: "Barbell Bench Press", muscle: "Chest", sets: 4, reps: "6–8", intensityTarget: "8"),
            .init(name: "Overhead Press", muscle: "Front delts", sets: 4, reps: "8–10", intensityTarget: "8"),
            .init(name: "Incline DB Press", muscle: "Upper chest", sets: 3, reps: "10–12", intensityTarget: "9"),
            .init(name: "Cable Lateral Raise", muscle: "Side delts", sets: 3, reps: "12–15", intensityTarget: "9"),
            .init(name: "Rope Triceps Pushdown", muscle: "Triceps", sets: 3, reps: "12", repMode: .target, intensityTarget: "9"),
        ]),
        .init(slotIndex: 1, name: "Pull A", muscleSummary: "Back · rear delts · biceps", exercises: [
            .init(name: "Weighted Pull-Up", muscle: "Lats", sets: 4, reps: "6–8", intensityTarget: "8"),
            .init(name: "Barbell Row", muscle: "Mid back", sets: 4, reps: "8–10", intensityTarget: "8"),
            .init(name: "Lat Pulldown", muscle: "Lats", sets: 3, reps: "10–12", intensityTarget: "9"),
            .init(name: "Face Pull", muscle: "Rear delts", sets: 3, reps: "15–20", intensityTarget: "9"),
            .init(name: "Barbell Curl", muscle: "Biceps", sets: 3, reps: "10–12", intensityTarget: "9"),
        ]),
        .init(slotIndex: 2, name: "Legs A", muscleSummary: "Quads · hams · calves", exercises: [
            .init(name: "Back Squat", muscle: "Quads", sets: 4, reps: "5–7", intensityTarget: "8"),
            .init(name: "Romanian Deadlift", muscle: "Hamstrings", sets: 3, reps: "8–10", intensityTarget: "8"),
            .init(name: "Leg Press", muscle: "Quads", sets: 3, reps: "12–15", intensityTarget: "9"),
            .init(name: "Seated Leg Curl", muscle: "Hamstrings", sets: 3, reps: "12–15", intensityTarget: "9"),
            .init(name: "Standing Calf Raise", muscle: "Calves", sets: 4, reps: "12", repMode: .target, intensityTarget: "9"),
        ]),
        restSlot(3),
        .init(slotIndex: 4, name: "Push B", muscleSummary: "Shoulders · chest · triceps", exercises: [
            .init(name: "Seated DB Press", muscle: "Front delts", sets: 4, reps: "8–10", intensityTarget: "8"),
            .init(name: "Incline Barbell Press", muscle: "Upper chest", sets: 4, reps: "6–8", intensityTarget: "8"),
            .init(name: "Pec Deck", muscle: "Chest", sets: 3, reps: "12–15", intensityTarget: "9"),
            .init(name: "Lateral Raise", muscle: "Side delts", sets: 4, reps: "15", repMode: .target, intensityTarget: "9"),
            .init(name: "Overhead Triceps Extension", muscle: "Triceps", sets: 3, reps: "10–12", intensityTarget: "9"),
        ]),
        .init(slotIndex: 5, name: "Pull B", muscleSummary: "Back · traps · biceps", exercises: [
            .init(name: "Deadlift", muscle: "Posterior chain", sets: 3, reps: "5", repMode: .target, intensityTarget: "8"),
            .init(name: "Chest-Supported Row", muscle: "Mid back", sets: 4, reps: "10–12", intensityTarget: "9"),
            .init(name: "Single-Arm Pulldown", muscle: "Lats", sets: 3, reps: "12–15", intensityTarget: "9"),
            .init(name: "Shrug", muscle: "Traps", sets: 3, reps: "12–15", intensityTarget: "9"),
            .init(name: "Incline DB Curl", muscle: "Biceps", sets: 3, reps: "10–12", intensityTarget: "9"),
        ]),
        .init(slotIndex: 6, name: "Legs B", muscleSummary: "Hams · quads · glutes", exercises: [
            .init(name: "Front Squat", muscle: "Quads", sets: 4, reps: "6–8", intensityTarget: "8"),
            .init(name: "Hip Thrust", muscle: "Glutes", sets: 3, reps: "8–10", intensityTarget: "8"),
            .init(name: "Walking Lunge", muscle: "Quads", sets: 3, reps: "12", repMode: .target, intensityTarget: "9"),
            .init(name: "Lying Leg Curl", muscle: "Hamstrings", sets: 3, reps: "12–15", intensityTarget: "9"),
            .init(name: "Seated Calf Raise", muscle: "Calves", sets: 4, reps: "15", repMode: .target, intensityTarget: "9"),
        ]),
        restSlot(7),
    ]

    /// Upper/Lower microcycle — four slots: Upper, Lower, Rest, repeat-ish.
    private static let upperLowerDays: [ProgramDay] = [
        .init(slotIndex: 0, name: "Upper A", muscleSummary: "Chest · back · arms", exercises: [
            .init(name: "Bench Press", muscle: "Chest", sets: 4, reps: "5–7", intensityTarget: "8"),
            .init(name: "Barbell Row", muscle: "Mid back", sets: 4, reps: "6–8", intensityTarget: "8"),
            .init(name: "Overhead Press", muscle: "Front delts", sets: 3, reps: "8–10", intensityTarget: "9"),
            .init(name: "Lat Pulldown", muscle: "Lats", sets: 3, reps: "10–12", intensityTarget: "9"),
        ]),
        .init(slotIndex: 1, name: "Lower A", muscleSummary: "Quads · hams · calves", exercises: [
            .init(name: "Back Squat", muscle: "Quads", sets: 4, reps: "5–7", intensityTarget: "8"),
            .init(name: "Romanian Deadlift", muscle: "Hamstrings", sets: 3, reps: "8–10", intensityTarget: "8"),
            .init(name: "Leg Extension", muscle: "Quads", sets: 3, reps: "12–15", intensityTarget: "9"),
            .init(name: "Standing Calf Raise", muscle: "Calves", sets: 4, reps: "12", repMode: .target, intensityTarget: "9"),
        ]),
        restSlot(2),
    ]

    private static let fiveThreeOneDays: [ProgramDay] = [
        .init(slotIndex: 0, name: "Press Day", muscleSummary: "Shoulders · chest", exercises: [
            .init(name: "Overhead Press", muscle: "Front delts", sets: 3, reps: "5", repMode: .target, intensityTarget: "8"),
            .init(name: "Bench Press · BBB", muscle: "Chest", sets: 5, reps: "10", repMode: .target, intensityTarget: "7"),
            .init(name: "Chin-Up", muscle: "Lats", sets: 5, reps: "10", repMode: .target, intensityTarget: "8"),
        ]),
        .init(slotIndex: 1, name: "Deadlift Day", muscleSummary: "Posterior chain", exercises: [
            .init(name: "Deadlift", muscle: "Posterior chain", sets: 3, reps: "5", repMode: .target, intensityTarget: "8"),
            .init(name: "Squat · BBB", muscle: "Quads", sets: 5, reps: "10", repMode: .target, intensityTarget: "7"),
            .init(name: "Hanging Leg Raise", muscle: "Abs", sets: 5, reps: "15", repMode: .target, intensityTarget: "8"),
        ]),
        restSlot(2),
    ]

    /// Same 5/3/1 BBB layout but with reps-in-reserve targets (0–3) for the
    /// `.rir` "My programs" entry — the `fiveThreeOneDays` above keeps RPE
    /// values for the templates, which render as RPE.
    private static let fiveThreeOneRIRDays: [ProgramDay] = [
        .init(slotIndex: 0, name: "Press Day", muscleSummary: "Shoulders · chest", exercises: [
            .init(name: "Overhead Press", muscle: "Front delts", sets: 3, reps: "5", repMode: .target, intensityTarget: "2"),
            .init(name: "Bench Press · BBB", muscle: "Chest", sets: 5, reps: "10", repMode: .target, intensityTarget: "3"),
            .init(name: "Chin-Up", muscle: "Lats", sets: 5, reps: "10", repMode: .target, intensityTarget: "2"),
        ]),
        .init(slotIndex: 1, name: "Deadlift Day", muscleSummary: "Posterior chain", exercises: [
            .init(name: "Deadlift", muscle: "Posterior chain", sets: 3, reps: "5", repMode: .target, intensityTarget: "2"),
            .init(name: "Squat · BBB", muscle: "Quads", sets: 5, reps: "10", repMode: .target, intensityTarget: "3"),
            .init(name: "Hanging Leg Raise", muscle: "Abs", sets: 5, reps: "15", repMode: .target, intensityTarget: "2"),
        ]),
        restSlot(2),
    ]

    static let myPrograms: [Program] = [
        .init(name: "PPL — Vanilla", goal: "Hypertrophy",
              progressionStrategy: "Double progression", intensityMode: .rpe,
              microcycleLength: pplDays.count, mesocycleLengthMicrocycles: 4,
              autoDeload: true, currentSlotIndex: 1, currentRepetition: 2,
              inDeload: false, active: true,
              days: pplDays),
        .init(name: "5/3/1 BBB", goal: "Strength",
              progressionStrategy: "Linear · TM cycles", intensityMode: .rir,
              microcycleLength: fiveThreeOneRIRDays.count, mesocycleLengthMicrocycles: 6,
              autoDeload: false, days: fiveThreeOneRIRDays),
        .init(name: "Upper/Lower (cut)", goal: "Recomp",
              progressionStrategy: "Hold load · cut", intensityMode: .off,
              microcycleLength: upperLowerDays.count, mesocycleLengthMicrocycles: 3,
              autoDeload: true, days: upperLowerDays),
    ]

    static let templates: [ProgramTemplate] = [
        .init(name: "PPL — Vanilla", category: .hypertrophy,
              description: "Push / Pull / Legs across an eight-slot microcycle. Double-progression on the compounds, high-rep isolation accessories.",
              goal: "Hypertrophy", microcycleLength: pplDays.count, mesocycleLengthMicrocycles: 4,
              visibility: .curated, rating: "4.9", active: true,
              days: pplDays),
        .init(name: "Upper / Lower", category: .hypertrophy,
              description: "Alternating upper- and lower-body slots with a rest slot. Balanced volume, easy to recover from.",
              goal: "Hypertrophy", microcycleLength: upperLowerDays.count, mesocycleLengthMicrocycles: 4,
              visibility: .curated, rating: "4.7",
              days: upperLowerDays),
        .init(name: "5/3/1 BBB", category: .strength,
              description: "Wendler's classic with Boring But Big back-off volume. Slow, reliable strength on the main lifts.",
              goal: "Strength", microcycleLength: fiveThreeOneDays.count, mesocycleLengthMicrocycles: 6,
              visibility: .curated, rating: "4.8",
              days: fiveThreeOneDays),
        .init(name: "Starting Strength", category: .strength,
              description: "Three full-body slots, linear progression on squat, press and deadlift. Built for novices.",
              goal: "Strength", microcycleLength: fiveThreeOneDays.count, mesocycleLengthMicrocycles: 6,
              visibility: .curated, rating: "4.6",
              days: fiveThreeOneDays),
        .init(name: "My PPL (tweaked)", category: .hypertrophy,
              description: "A saved copy of the vanilla PPL with extra arm volume — kept private to me.",
              goal: "Hypertrophy", microcycleLength: pplDays.count, mesocycleLengthMicrocycles: 4,
              visibility: .private, ownerIsMe: true, rating: "—",
              days: pplDays),
        .init(name: "Partner Block A", category: .general,
              description: "Shared by a training partner — balanced full-body slots with a built-in rest slot.",
              goal: "General", microcycleLength: upperLowerDays.count, mesocycleLengthMicrocycles: 4,
              visibility: .shared, ownerIsMe: true, rating: "4.7",
              days: upperLowerDays),
    ]

    /// A representative microcycle for editor / per-slot previews.
    static var sampleWeek: [ProgramDay] { pplDays }

    /// Blank-slate seed for "build your own".
    static let blankProgram = Program(
        name: "New program", goal: "Hypertrophy",
        progressionStrategy: "Double progression", intensityMode: .rpe,
        microcycleLength: 1, mesocycleLengthMicrocycles: 4, autoDeload: true,
        days: [
            .init(slotIndex: 0, name: "Day 1", muscleSummary: "", exercises: [
                .init(name: "Barbell Bench Press", muscle: "Chest", sets: 4, reps: "6–8", intensityTarget: "8"),
            ]),
        ]
    )

    // MARK: Calendar (May 2026 — starts Friday, 31 days, today = 27)

    struct CalendarDay: Identifiable {
        let id = UUID()
        let day: Int?          // nil = leading blank
        var workout: String? = nil
        var completed = false
        var today = false
        var future = false
    }

    static let calendarTitle = "May 2026"
    static let calendarWeekdays = ["S", "M", "T", "W", "T", "F", "S"]

    static let calendarDays: [CalendarDay] = {
        // May 1, 2026 is a Friday → 5 leading blanks (S,M,T,W,T).
        let planned: [Int: String] = [
            1: "Push A", 2: "Legs A", 4: "Pull A", 5: "Push B", 6: "Legs B", 8: "Pull B",
            9: "Push A", 11: "Legs A", 12: "Pull A", 13: "Push B", 15: "Legs B", 16: "Pull B",
            17: "Push A", 19: "Push B", 20: "Pull B", 21: "Legs B", 23: "Push A", 24: "Pull A",
            26: "Legs A", 27: "Push A", 28: "Pull A", 30: "Push B", 31: "Legs B",
        ]
        let completed: Set<Int> = [1, 2, 4, 5, 6, 8, 9, 11, 12, 13, 15, 16, 17, 19, 20, 21, 23, 24, 26]
        var days: [CalendarDay] = (0..<5).map { _ in CalendarDay(day: nil) }
        for d in 1...31 {
            days.append(CalendarDay(
                day: d,
                workout: planned[d],
                completed: completed.contains(d),
                today: d == 27,
                future: d > 27
            ))
        }
        return days
    }()

    // MARK: Food search (Add Food sheet)

    struct SearchFood: Identifiable {
        let id = UUID()
        let name: String
        let brand: String?
        let kcalPer100: Int
        let protein: Int
        var favorite = false
    }

    static let recentFoods: [SearchFood] = [
        .init(name: "Oats, rolled", brand: "Bob's Red Mill", kcalPer100: 380, protein: 13, favorite: true),
        .init(name: "Whey isolate", brand: "Optimum", kcalPer100: 390, protein: 80, favorite: true),
        .init(name: "Chicken thigh, grilled", brand: nil, kcalPer100: 205, protein: 26),
        .init(name: "Greek yogurt, 2%", brand: "Fage", kcalPer100: 65, protein: 9, favorite: true),
        .init(name: "Jasmine rice, cooked", brand: nil, kcalPer100: 130, protein: 3),
        .init(name: "Banana", brand: nil, kcalPer100: 89, protein: 1),
    ]

    // MARK: Nutrition plans

    /// One meal in a plan template (Direction A plan mode renders these slots).
    struct NutritionMealSlot: Identifiable {
        let id = UUID()
        let name: String
        var kcal: Int? = nil
        var protein: Int? = nil
        var carbs: Int? = nil
        var fat: Int? = nil
    }

    struct NutritionPlan: Identifiable {
        let id = UUID()
        let name: String
        let kcal: Int
        let protein: Int
        let carbs: Int
        let fat: Int
        var active = false
        var slots: [NutritionMealSlot] = []
    }

    static let nutritionPlans: [NutritionPlan] = [
        .init(name: "Lean bulk", kcal: 2_680, protein: 200, carbs: 300, fat: 80, active: true,
              slots: [
                .init(name: "Pre-workout", kcal: 520, protein: 40, carbs: 60, fat: 12),
                .init(name: "Post-workout", kcal: 880, protein: 70, carbs: 110, fat: 18),
                .init(name: "Dinner", kcal: 1_280, protein: 90, carbs: 130, fat: 50),
              ]),
        .init(name: "Maintenance", kcal: 2_400, protein: 180, carbs: 260, fat: 75),
        .init(name: "Cut", kcal: 2_050, protein: 200, carbs: 180, fat: 60),
    ]

    /// The currently-active plan (drives plan-mode slots on the day screen).
    static var activePlan: NutritionPlan? {
        nutritionPlans.first { $0.active }
    }

    /// Daily kcal totals for the nutrition history strip (last 14 days).
    struct DayTotal: Identifiable {
        let id = UUID()
        let label: String
        let kcal: Int
    }

    static let nutritionHistory: [DayTotal] = {
        let vals = [2520, 2610, 2480, 2700, 2350, 2680, 2590, 2440, 2720, 2510, 2630, 2480, 2660, 1620]
        return vals.enumerated().map { i, v in DayTotal(label: "\(i + 14)", kcal: v) }
    }()

    static let nutritionAdherence = "11 / 14 days on target"

    // MARK: Heat ramp helper

    /// Accent-tinted opacity for a heat level 0...4.
    static func heatOpacity(_ level: Int) -> Double {
        switch level {
        case 1: return 0.16
        case 2: return 0.34
        case 3: return 0.62
        case 4: return 1.0
        default: return 0.0
        }
    }
}
