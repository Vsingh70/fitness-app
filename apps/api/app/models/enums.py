from enum import StrEnum


class UnitSystem(StrEnum):
    metric = "metric"
    imperial = "imperial"


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


class ProgramGoal(StrEnum):
    hypertrophy = "hypertrophy"
    strength = "strength"
    powerbuilding = "powerbuilding"
    fat_loss = "fat_loss"
    general = "general"
    custom = "custom"


class ProgramSource(StrEnum):
    template = "template"
    manual = "manual"
    copied = "copied"


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
