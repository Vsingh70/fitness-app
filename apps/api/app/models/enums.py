from enum import StrEnum


class UnitSystem(StrEnum):
    metric = "metric"
    imperial = "imperial"


class NutritionMode(StrEnum):
    flexible = "flexible"
    plan = "plan"


class SexAtBirth(StrEnum):
    male = "male"
    female = "female"
    other = "other"


class Muscle(StrEnum):
    chest = "chest"
    lats = "lats"
    traps = "traps"
    rhomboids = "rhomboids"
    rear_delts = "rear_delts"
    side_delts = "side_delts"
    front_delts = "front_delts"
    biceps = "biceps"
    triceps = "triceps"
    forearms = "forearms"
    abs = "abs"
    obliques = "obliques"
    lower_back = "lower_back"
    glutes = "glutes"
    quads = "quads"
    hamstrings = "hamstrings"
    adductors = "adductors"
    abductors = "abductors"
    calves = "calves"


class Equipment(StrEnum):
    barbell = "barbell"
    dumbbell = "dumbbell"
    cable = "cable"
    machine = "machine"
    bodyweight = "bodyweight"
    banded = "banded"
    kettlebell = "kettlebell"
    smith_machine = "smith_machine"
    trap_bar = "trap_bar"
    ez_bar = "ez_bar"
    plate_loaded = "plate_loaded"
    cardio_machine = "cardio_machine"
    other = "other"


class MovementPattern(StrEnum):
    squat = "squat"
    hinge = "hinge"
    horizontal_push = "horizontal_push"
    vertical_push = "vertical_push"
    horizontal_pull = "horizontal_pull"
    vertical_pull = "vertical_pull"
    lunge = "lunge"
    carry = "carry"
    rotation = "rotation"
    anti_rotation = "anti_rotation"
    isolation = "isolation"
    cardio = "cardio"
    mobility = "mobility"
    plyometric = "plyometric"


class TrackingType(StrEnum):
    weight_reps = "weight_reps"
    weight_reps_distance = "weight_reps_distance"
    weight_time = "weight_time"
    bodyweight_reps = "bodyweight_reps"
    weighted_bodyweight = "weighted_bodyweight"
    time_only = "time_only"
    distance_time = "distance_time"
    distance_time_pace = "distance_time_pace"
    cardio_machine = "cardio_machine"


class SetType(StrEnum):
    working = "working"
    warmup = "warmup"
    drop = "drop"
    myo_rep = "myo_rep"
    cluster = "cluster"
    top_set = "top_set"
    back_off = "back_off"
    amrap = "amrap"
    interval = "interval"


class SegmentKind(StrEnum):
    work = "work"
    rest = "rest"
    mini_set = "mini_set"


class BlockKind(StrEnum):
    warmup = "warmup"
    working = "working"
    cooldown = "cooldown"


class ProgramGoal(StrEnum):
    hypertrophy = "hypertrophy"
    strength = "strength"
    powerbuilding = "powerbuilding"
    fat_loss = "fat_loss"
    endurance = "endurance"
    general = "general"
    custom = "custom"


class ProgramSource(StrEnum):
    template = "template"
    manual = "manual"
    copied = "copied"


class TemplateVisibility(StrEnum):
    private = "private"
    shared = "shared"


class PeriodizationMode(StrEnum):
    block = "block"
    continuous = "continuous"


class IntensityMode(StrEnum):
    rpe = "rpe"
    rir = "rir"
    off = "off"


class RepMode(StrEnum):
    range = "range"
    target = "target"


class ProgressionStrategy(StrEnum):
    linear = "linear"
    double_progression = "double_progression"
    rpe_based = "rpe_based"
    none = "none"


class ScheduledWorkoutStatus(StrEnum):
    planned = "planned"
    in_progress = "in_progress"
    completed = "completed"
    skipped = "skipped"


class NotificationKind(StrEnum):
    workout_reminder = "workout_reminder"


class RecommendationKind(StrEnum):
    increase_weight = "increase_weight"
    increase_reps = "increase_reps"
    hold = "hold"
    deload = "deload"
    swap = "swap"
    add_set = "add_set"
    remove_set = "remove_set"


class AnalyticsInsightKind(StrEnum):
    stagnation = "stagnation"
    volume_drop = "volume_drop"
    frequency_drop = "frequency_drop"
    pr_streak = "pr_streak"
    weak_muscle = "weak_muscle"
    strong_muscle = "strong_muscle"
    imbalance = "imbalance"
    undertrained = "undertrained"


class AnalyticsInsightSeverity(StrEnum):
    info = "info"
    warn = "warn"
    action = "action"


class FoodSource(StrEnum):
    usda = "usda"
    off = "off"
    custom = "custom"
    user = "user"
    # NOTE: the underlying Postgres ``food_source`` enum also carries a legacy
    # ``fatsecret`` value (added in migration 0021). FatSecret was removed before
    # going live; no row ever used it, and Postgres cannot drop an enum value, so
    # the DB value is left dormant and intentionally absent from this Python enum.


class ServingUnit(StrEnum):
    g = "g"
    ml = "ml"


class MealPlanItemUnit(StrEnum):
    g = "g"
    ml = "ml"
    serving = "serving"


class MealType(StrEnum):
    breakfast = "breakfast"
    lunch = "lunch"
    dinner = "dinner"
    snack = "snack"


class MealPlanKind(StrEnum):
    daily_repeating = "daily_repeating"
    training_rest = "training_rest"
    weekly = "weekly"


class MealPlanContentMode(StrEnum):
    targets_only = "targets_only"
    meals_only = "meals_only"
    targets_and_meals = "targets_and_meals"


class MealPlanTrackingMode(StrEnum):
    calories_only = "calories_only"
    macros_only = "macros_only"
    macros_and_calories = "macros_and_calories"


class MealPlanDayRole(StrEnum):
    every_day = "every_day"
    training = "training"
    rest = "rest"
    dow_0 = "dow_0"
    dow_1 = "dow_1"
    dow_2 = "dow_2"
    dow_3 = "dow_3"
    dow_4 = "dow_4"
    dow_5 = "dow_5"
    dow_6 = "dow_6"
