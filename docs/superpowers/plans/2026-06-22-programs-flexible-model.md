# Programs Flexible Microcycle/Mesocycle Model — Implementation Plan

> **Plan 1 of 3** in the Programs vertical slice (`tasks/redesign/`). This plan is the
> backend gate: it must land and ship working before Plans 2 (responsive + motion
> foundation) and 3 (Programs web UI) can build on it. Plans 2 and 3 are outlined in the
> Roadmap section at the end and will be fully detailed after this one is merged.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps
> use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the rigid `days_per_week`/`weeks` program model with a flexible
microcycle (ordered training/rest slots, any length) repeated into a mesocycle, advanced
by pure rotation, with template duplicate/save-as-template and deactivate support.

**Architecture:** Slots replace weekday-bound days (`program_days.slot_index` +
`is_rest_day`). A new `program_progress` table holds per-user-per-program rotation
position. The legacy calendar scheduler (`_generate_schedule_rows`, continuous rolling
calendar, block/continuous `mesocycle_week` math) is replaced by a small rotation engine
that advances a position on session complete/skip. `scheduled_workouts` is kept but
loosened (nullable `scheduled_for`, `microcycle_number`/`repetition` instead of
`mesocycle_week`) and the calendar is projected from the rotation rather than pre-generated.

**Tech Stack:** FastAPI, SQLAlchemy 2.0 (async, `Mapped`/`mapped_column`), Alembic,
Pydantic v2, PostgreSQL (asyncpg), pytest + testcontainers, OpenAPI codegen
(`packages/openapi/openapi.json` → web types via `pnpm openapi:generate`).

---

## Decisions taken in this plan (confirm before execution)

These follow the redesign specs but resolve two ambiguities the specs leave open. Flag if
either is wrong:

1. **Rest-day advance.** A rest slot is consumed by an explicit one-tap advance, not by the
   passage of a calendar day. The rotation engine exposes `POST /programs/{id}/advance`
   (used by the rest-day "Done" affordance and, later in Plan 06, by session completion).
   "Pure rotation" stays honest: you only move when you act.
2. **`scheduled_workouts` is retained but demoted.** The legacy block/continuous schedule
   generation is **deleted**. The calendar surface (Plan for IA, later) projects the
   rotation forward in memory from `program_progress` + slots. `scheduled_workouts` rows
   are still written on session start/skip for history, with `scheduled_for` nullable and
   `microcycle_number`/`repetition` replacing `mesocycle_week`. The continuous-periodization
   rolling-calendar code is removed; `periodization_mode` is retained on the model (it still
   gates deload behavior) but no longer drives a calendar.

If decision 2 is too aggressive for one PR, Task 6 can be split: land the rotation engine
first, delete legacy scheduling in a follow-up. The tasks are ordered so that's possible.

---

## File structure

**Backend (`apps/api`):**

- `app/models/program.py` — modify `Program`, `ProgramDay`, `ProgramTemplate`; the new
  `template_visibility` enum imports.
- `app/models/program_progress.py` — **new** `ProgramProgress` model.
- `app/models/scheduled_workout.py` — modify columns.
- `app/models/enums.py` (or wherever `ProgramGoal`/`IntensityMode` live) — add
  `TemplateVisibility` enum.
- `app/schemas/program.py` — reshape every program schema.
- `app/services/programs.py` — slot CRUD, activation, duplicate, save-as-template, template
  list visibility; **delete** legacy scheduling.
- `app/services/rotation.py` — **new** rotation engine (position + advance).
- `app/routers/programs.py` — new/changed endpoints.
- `alembic/versions/20260622_0027_flexible_microcycle_mesocycle.py` — **new** migration.
- `seed/programs/_dsl.py` + `seed/programs/*.py` + `scripts/seed_programs.py` — slots shape.
- `tasks/00-overview/data-model.md` — update schema reference.

**Tests (`apps/api/tests`):**

- `tests/test_program_builder_api.py` — update existing assertions to the new shape.
- `tests/test_program_slots_api.py` — **new** slot add/reorder/rest-toggle.
- `tests/test_rotation_engine.py` — **new** unit tests for the rotation math.
- `tests/test_program_rotation_api.py` — **new** activate → position → advance → wrap →
  deload integration.
- `tests/test_program_templates_api.py` — **new** duplicate, save-as-template, visibility.

**Generated:**

- `packages/openapi/openapi.json` + `apps/web/src/lib/api/types.ts` — regenerated, last.

---

## Task 1: Add the `TemplateVisibility` enum and `ProgramProgress` model

**Files:**
- Modify: `app/models/program.py` (enum import + template columns done in Task 2; enum
  definition here)
- Create: `app/models/program_progress.py`
- Find the enum module: the report shows `ProgramGoal`, `IntensityMode`, `RepMode`,
  `PeriodizationMode`, `ProgramSource` are defined alongside the models. Define
  `TemplateVisibility` in the same place those live.

- [ ] **Step 1: Locate the enum definitions**

Run: `grep -rn "class ProgramGoal" apps/api/app`
Expected: one hit (e.g. `app/models/program.py` or `app/models/enums.py`). Add the new
enum in that file.

- [ ] **Step 2: Add the `TemplateVisibility` enum**

In the file from Step 1, beside `ProgramSource`:

```python
import enum


class TemplateVisibility(enum.StrEnum):
    private = "private"
    shared = "shared"
```

(Match the existing enum base class used by `ProgramGoal` — if they subclass `str, enum.Enum`
instead of `enum.StrEnum`, mirror that exactly.)

- [ ] **Step 3: Create the `ProgramProgress` model**

Create `app/models/program_progress.py`, mirroring the column/typing style of
`app/models/scheduled_workout.py`:

```python
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base  # match the import other models use
from app.models._ids import uuid7  # match how other models default ids


class ProgramProgress(Base):
    __tablename__ = "program_progress"
    __table_args__ = (
        UniqueConstraint("user_id", "program_id", name="uq_program_progress_user_program"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    program_id: Mapped[UUID] = mapped_column(
        ForeignKey("programs.id", ondelete="CASCADE"), index=True, nullable=False
    )
    current_slot_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    current_microcycle_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    current_repetition: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    in_deload: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=...,  # mirror other models' server_default=now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=...,
    )
```

Copy the exact `Base` import, id default, and `server_default` expression from
`scheduled_workout.py` so this file is consistent with the codebase.

- [ ] **Step 4: Register the model for metadata**

Run: `grep -rn "scheduled_workout" apps/api/app/models/__init__.py`
If `__init__.py` imports each model, add `from app.models.program_progress import ProgramProgress`
in the same style so Alembic autogenerate/`Base.metadata` sees it.

- [ ] **Step 5: Verify it imports**

Run: `cd apps/api && uv run python -c "from app.models.program_progress import ProgramProgress; print(ProgramProgress.__tablename__)"`
Expected: `program_progress`

- [ ] **Step 6: Commit**

```bash
git add apps/api/app/models/program_progress.py apps/api/app/models/program.py apps/api/app/models/__init__.py
git commit -m "feat(api): add ProgramProgress model and TemplateVisibility enum"
```

---

## Task 2: Reshape the `Program`, `ProgramDay`, `ProgramTemplate`, `ScheduledWorkout` models

**Files:**
- Modify: `app/models/program.py:53-152` (Program, ProgramDay, ProgramTemplate)
- Modify: `app/models/scheduled_workout.py:14-58`

No migration yet (Task 3). These are the ORM column edits.

- [ ] **Step 1: Edit `Program`**

In `app/models/program.py`, in `Program`:
- Remove `weeks` and `days_per_week` columns.
- Add `microcycle_length: Mapped[int] = mapped_column(Integer, nullable=False, default=0)`.
- Rename `mesocycle_length_weeks` → `mesocycle_length_microcycles` (keep `Integer`,
  `nullable=False`, `default=4`).
- Keep everything else (`goal`, `source`, `template_id`, `is_active`, `activated_at`,
  `deleted_at`, `auto_deload`, `periodization_mode`, `auto_deload_on_stall`,
  `intensity_mode`).
- Add a relationship to progress if useful:
  `progress: Mapped[list["ProgramProgress"]] = relationship(cascade="all, delete-orphan")`
  (optional; only if other code wants it).

- [ ] **Step 2: Edit `ProgramDay`**

- Rename `day_index` → `slot_index` (`Integer`, `nullable=False`).
- Add `is_rest_day: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)`.
- Update the `Program.days` relationship `order_by` from `ProgramDay.day_index` to
  `ProgramDay.slot_index`.
- `name` stays `nullable=False`; service layer defaults rest-slot names to "Rest".

- [ ] **Step 3: Edit `ProgramTemplate`**

- Remove `weeks`, `days_per_week`.
- Add `microcycle_length: Mapped[int]` (`Integer`, `nullable=False`, default 0).
- Add `mesocycle_length_microcycles: Mapped[int]` (`Integer`, `nullable=False`, default 4).
- Add `owner_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)`.
- Add `visibility: Mapped[TemplateVisibility | None] = mapped_column(... nullable=True)`
  using the same `postgresql.ENUM`/`SAEnum` pattern the other enum columns use in this file
  (mirror how `goal`/`intensity_mode` are declared). Null = curated.

- [ ] **Step 4: Edit `ScheduledWorkout`**

In `app/models/scheduled_workout.py`:
- Make `scheduled_for` nullable: `Mapped[date | None] = mapped_column(Date, nullable=True, index=True)`.
- Remove `mesocycle_week`.
- Add `microcycle_number: Mapped[int | None] = mapped_column(Integer, nullable=True)`.
- Add `repetition: Mapped[int | None] = mapped_column(Integer, nullable=True)`.
- Keep `is_deload`, `status`, FKs.

- [ ] **Step 5: Verify import**

Run: `cd apps/api && uv run python -c "import app.models.program, app.models.scheduled_workout; print('ok')"`
Expected: `ok`

- [ ] **Step 6: Commit**

```bash
git add apps/api/app/models/program.py apps/api/app/models/scheduled_workout.py
git commit -m "feat(api): reshape program models to microcycle slots (no migration yet)"
```

---

## Task 3: Alembic migration `0027_flexible_microcycle_mesocycle`

**Files:**
- Create: `alembic/versions/20260622_0027_flexible_microcycle_mesocycle.py`

Follow the exact style of `20260611_0026_program_intensity_rep_mode.py`: revision id string
`"0027_flexible_microcycle_mesocycle"`, `down_revision = "0026_program_intensity_rep_mode"`,
enum via `postgresql.ENUM(..., create_type=True)`, `op.add_column`, `op.execute` for
backfill, server defaults via `sa.text()`.

- [ ] **Step 1: Write the migration `upgrade()`**

```python
"""flexible microcycle/mesocycle program model

Revision ID: 0027_flexible_microcycle_mesocycle
Revises: 0026_program_intensity_rep_mode
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0027_flexible_microcycle_mesocycle"
down_revision = "0026_program_intensity_rep_mode"
branch_labels = None
depends_on = None

template_visibility = postgresql.ENUM(
    "private", "shared", name="template_visibility", create_type=False
)


def upgrade() -> None:
    bind = op.get_bind()
    template_visibility.create(bind, checkfirst=True)

    # --- programs: add new, backfill, drop old ---
    op.add_column("programs", sa.Column("microcycle_length", sa.Integer(), nullable=True))
    op.add_column(
        "programs",
        sa.Column("mesocycle_length_microcycles", sa.Integer(), nullable=True),
    )
    op.execute("UPDATE programs SET microcycle_length = days_per_week")
    op.execute(
        "UPDATE programs SET mesocycle_length_microcycles = mesocycle_length_weeks"
    )
    op.alter_column("programs", "microcycle_length", nullable=False)
    op.alter_column(
        "programs",
        "mesocycle_length_microcycles",
        nullable=False,
        server_default=sa.text("4"),
    )
    op.drop_column("programs", "days_per_week")
    op.drop_column("programs", "weeks")
    op.drop_column("programs", "mesocycle_length_weeks")

    # --- program_days: rename day_index -> slot_index, add is_rest_day ---
    op.alter_column("program_days", "day_index", new_column_name="slot_index")
    op.add_column(
        "program_days",
        sa.Column(
            "is_rest_day",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )

    # --- program_templates: reshape ---
    op.add_column(
        "program_templates", sa.Column("microcycle_length", sa.Integer(), nullable=True)
    )
    op.add_column(
        "program_templates",
        sa.Column("mesocycle_length_microcycles", sa.Integer(), nullable=True),
    )
    op.add_column(
        "program_templates",
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "program_templates",
        sa.Column("visibility", template_visibility, nullable=True),
    )
    op.create_foreign_key(
        "fk_program_templates_owner",
        "program_templates",
        "users",
        ["owner_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(
        "ix_program_templates_owner_id", "program_templates", ["owner_id"]
    )
    op.execute("UPDATE program_templates SET microcycle_length = days_per_week")
    op.execute("UPDATE program_templates SET mesocycle_length_microcycles = 4")
    op.alter_column("program_templates", "microcycle_length", nullable=False)
    op.alter_column(
        "program_templates", "mesocycle_length_microcycles", nullable=False
    )
    op.drop_column("program_templates", "days_per_week")
    op.drop_column("program_templates", "weeks")

    # --- scheduled_workouts: loosen date, swap mesocycle_week ---
    op.add_column(
        "scheduled_workouts", sa.Column("microcycle_number", sa.Integer(), nullable=True)
    )
    op.add_column(
        "scheduled_workouts", sa.Column("repetition", sa.Integer(), nullable=True)
    )
    op.execute(
        "UPDATE scheduled_workouts SET microcycle_number = mesocycle_week"
    )
    op.alter_column("scheduled_workouts", "scheduled_for", nullable=True)
    op.drop_column("scheduled_workouts", "mesocycle_week")

    # --- program_progress: new table ---
    op.create_table(
        "program_progress",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("program_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("current_slot_index", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("current_microcycle_number", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("current_repetition", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("in_deload", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("last_completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["program_id"], ["programs.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "program_id", name="uq_program_progress_user_program"),
    )
    op.create_index("ix_program_progress_user_id", "program_progress", ["user_id"])
    op.create_index("ix_program_progress_program_id", "program_progress", ["program_id"])
```

- [ ] **Step 2: Write `downgrade()`**

Mirror in reverse (recreate `weeks`/`days_per_week`/`mesocycle_week` as nullable then drop
new). A best-effort downgrade is acceptable per the breaking-change latitude in
`01-program-model.md §3`; do not lose existing rows. At minimum: drop `program_progress`,
re-add `mesocycle_week` (backfill from `microcycle_number`), re-add `days_per_week`/`weeks`
(backfill from `microcycle_length`/constant), reverse the rename, drop the enum.

- [ ] **Step 3: Run the migration up against a scratch DB**

Run: `cd apps/api && uv run alembic upgrade head`
Expected: completes; `0027` is head. Verify: `uv run alembic current` shows `0027...`.

- [ ] **Step 4: Round-trip test**

Run: `cd apps/api && uv run alembic downgrade -1 && uv run alembic upgrade head`
Expected: both succeed with no error.

- [ ] **Step 5: Commit**

```bash
git add apps/api/alembic/versions/20260622_0027_flexible_microcycle_mesocycle.py
git commit -m "feat(api): migration 0027 flexible microcycle/mesocycle"
```

---

## Task 4: Reshape Pydantic schemas

**Files:**
- Modify: `app/schemas/program.py`

Apply these field changes (every `weeks`/`days_per_week`/`day_index`/`mesocycle_length_weeks`/
`mesocycle_week` reference from the backend report):

- `ProgramTemplateSummary`: drop `weeks`, `days_per_week`; add `microcycle_length: int`,
  `mesocycle_length_microcycles: int`, `owner_id: UUID | None`,
  `visibility: TemplateVisibility | None`.
- `ProgramDayResponse`: rename `day_index` → `slot_index`; add `is_rest_day: bool`.
- `ProgramResponse`: drop `weeks`, `days_per_week`; add `microcycle_length: int`; rename
  `mesocycle_length_weeks` → `mesocycle_length_microcycles`.
- `ProgramListItem`: drop `weeks`, `days_per_week`; add `microcycle_length: int`,
  `mesocycle_length_microcycles: int`.
- `ProgramCreate`: drop `weeks`, `days_per_week` (a new program has zero slots and
  microcycle_length 0). Keep `name`, `description`, `goal`, `periodization_mode`,
  `auto_deload_on_stall`, `intensity_mode`. **This removes the forced 6-week/4-day defaults.**
- `ProgramUpdate`: drop `weeks`, `days_per_week`; rename `mesocycle_length_weeks` →
  `mesocycle_length_microcycles` (`Field(ge=1)`); add `auto_deload: bool | None`.
- `ScheduledWorkoutResponse`: drop `mesocycle_week`; add `microcycle_number: int | None`,
  `repetition: int | None`; `scheduled_for: date | None`.

- [ ] **Step 1: Add the new slot + rotation + template schemas**

```python
class ProgramDayCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    is_rest_day: bool = False


class ProgramDayUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    is_rest_day: bool | None = None


class SlotReorderRequest(BaseModel):
    slot_ids: list[UUID]  # full ordered list of this program's slot ids


class ProgramPositionResponse(BaseModel):
    current_slot_index: int
    current_microcycle_number: int
    current_repetition: int
    mesocycle_length_microcycles: int
    in_deload: bool
    today_slot: ProgramDayResponse | None  # null if program has no slots
    is_rest_day: bool
    next_training_slot: ProgramDayResponse | None  # the next training slot if today is rest


class DuplicateProgramResponse(BaseModel):
    program: ProgramResponse


class SaveAsTemplateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    visibility: TemplateVisibility = TemplateVisibility.private


class SaveAsTemplateResponse(BaseModel):
    template: ProgramTemplateSummary
```

- [ ] **Step 2: Verify import**

Run: `cd apps/api && uv run python -c "import app.schemas.program as s; print(s.ProgramPositionResponse.model_json_schema()['title'])"`
Expected: `ProgramPositionResponse`

- [ ] **Step 3: Commit**

```bash
git add apps/api/app/schemas/program.py
git commit -m "feat(api): reshape program schemas to microcycle/mesocycle + slots"
```

---

## Task 5: Rotation engine (unit-tested first)

**Files:**
- Create: `app/services/rotation.py`
- Test: `tests/test_rotation_engine.py`

Pure functions over a plain dataclass so the math is testable without a DB.

- [ ] **Step 1: Write the failing unit test**

```python
# tests/test_rotation_engine.py
from app.services.rotation import RotationState, advance


def _state(**kw):
    base = dict(slot_index=0, repetition=1, microcycle_number=1, in_deload=False)
    base.update(kw)
    return RotationState(**base)


def test_advance_within_microcycle():
    # 4-slot cycle, meso length 3
    s = advance(_state(slot_index=0), microcycle_length=4, meso_length=3, auto_deload=True)
    assert (s.slot_index, s.repetition, s.in_deload) == (1, 1, False)


def test_wrap_to_next_repetition():
    s = advance(_state(slot_index=3), microcycle_length=4, meso_length=3, auto_deload=True)
    assert (s.slot_index, s.repetition, s.in_deload) == (0, 2, False)


def test_enter_deload_after_last_repetition():
    # repetition 3 is the last (meso_length 3); wrapping from it enters deload
    s = advance(_state(slot_index=3, repetition=3), microcycle_length=4, meso_length=3, auto_deload=True)
    assert s.in_deload is True
    assert (s.slot_index, s.repetition) == (0, 3)


def test_leave_deload_into_next_mesocycle():
    s = advance(
        _state(slot_index=3, repetition=3, in_deload=True),
        microcycle_length=4, meso_length=3, auto_deload=True,
    )
    assert s.in_deload is False
    assert (s.slot_index, s.repetition, s.microcycle_number) == (0, 1, 2)


def test_no_deload_rolls_straight_into_next_meso():
    s = advance(_state(slot_index=3, repetition=3), microcycle_length=4, meso_length=3, auto_deload=False)
    assert s.in_deload is False
    assert (s.slot_index, s.repetition, s.microcycle_number) == (0, 1, 2)
```

- [ ] **Step 2: Run it, verify it fails**

Run: `cd apps/api && uv run pytest tests/test_rotation_engine.py -v`
Expected: FAIL with `ModuleNotFoundError: app.services.rotation`

- [ ] **Step 3: Implement `app/services/rotation.py`**

```python
from __future__ import annotations

from dataclasses import dataclass, replace


@dataclass(frozen=True)
class RotationState:
    slot_index: int
    repetition: int
    microcycle_number: int
    in_deload: bool


def advance(
    state: RotationState,
    *,
    microcycle_length: int,
    meso_length: int,
    auto_deload: bool,
) -> RotationState:
    """Advance the rotation by one slot.

    Within a microcycle: slot_index += 1.
    At microcycle end (slot wraps to 0): if currently in a deload microcycle, leave it
    and start the next mesocycle's first repetition. Otherwise bump repetition; if we just
    finished the last repetition (== meso_length), enter the deload microcycle when
    auto_deload, else roll straight into the next mesocycle.
    """
    if microcycle_length <= 0:
        return state

    next_slot = state.slot_index + 1
    if next_slot < microcycle_length:
        return replace(state, slot_index=next_slot)

    # microcycle just completed -> wrap
    if state.in_deload:
        # deload microcycle finished -> next mesocycle
        return RotationState(
            slot_index=0,
            repetition=1,
            microcycle_number=state.microcycle_number + 1,
            in_deload=False,
        )

    if state.repetition >= meso_length:
        if auto_deload:
            # enter the appended deload microcycle (repetition held at meso_length)
            return replace(state, slot_index=0, in_deload=True)
        return RotationState(
            slot_index=0, repetition=1,
            microcycle_number=state.microcycle_number + 1, in_deload=False,
        )

    return replace(state, slot_index=0, repetition=state.repetition + 1)
```

- [ ] **Step 4: Run, verify pass**

Run: `cd apps/api && uv run pytest tests/test_rotation_engine.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add apps/api/app/services/rotation.py apps/api/tests/test_rotation_engine.py
git commit -m "feat(api): pure rotation engine with deload wrap"
```

---

## Task 6: Service layer — slot CRUD, position, advance, activation, delete legacy scheduling

**Files:**
- Modify: `app/services/programs.py`

This is the largest task. Work in the order below; each bullet mirrors an existing function
named in the backend report so the implementer has a concrete template.

- [ ] **Step 1: `create_empty_program` — remove forced defaults**

Edit `create_empty_program` (was lines ~296-313). Set `microcycle_length=0`,
`mesocycle_length_microcycles=4`, no `weeks`/`days_per_week`. No slots created.

- [ ] **Step 2: Slot helpers replace day helpers**

- `add_slot(user, program_id, payload: ProgramDayCreate)` (was `add_day`): append a
  `ProgramDay` with `slot_index = max+1`, `is_rest_day = payload.is_rest_day`, name (default
  "Rest" when rest and no name). After insert, set
  `program.microcycle_length = count(slots)`.
- `delete_slot(user, slot_id)` (was `delete_day`): delete + decrement higher `slot_index`;
  recompute `microcycle_length`.
- `reorder_slots(user, program_id, slot_ids)` — **new**: validate the id set equals the
  program's slots, assign `slot_index` by list order in one pass.
- `toggle_rest(user, slot_id, is_rest_day)` — **new**: set `is_rest_day`; when turning a
  training slot into rest, the spec keeps existing exercise rows hidden (do NOT delete them —
  they reappear if toggled back). When `is_rest_day=False`, expose the list again.
- `update_slot(user, slot_id, payload: ProgramDayUpdate)` — name/rest edits.

`microcycle_length` is always recomputed server-side; never trust a client value.

- [ ] **Step 3: `get_or_create_progress` + `get_position`**

```python
async def get_or_create_progress(session, user_id, program) -> ProgramProgress: ...

async def get_position(session, user, program_id) -> ProgramPositionResponse:
    program = await _load_program_full(...)  # eager slots+exercises, ownership check
    prog = await get_or_create_progress(...)
    slots = program.days  # ordered by slot_index
    today = slots[prog.current_slot_index] if slots else None
    is_rest = bool(today and today.is_rest_day)
    next_training = next(
        (s for s in slots[prog.current_slot_index + 1:] + slots[: prog.current_slot_index]
         if not s.is_rest_day),
        None,
    ) if is_rest else None
    return ProgramPositionResponse(
        current_slot_index=prog.current_slot_index,
        current_microcycle_number=prog.current_microcycle_number,
        current_repetition=prog.current_repetition,
        mesocycle_length_microcycles=program.mesocycle_length_microcycles,
        in_deload=prog.in_deload,
        today_slot=_day_to_response(today) if today else None,
        is_rest_day=is_rest,
        next_training_slot=_day_to_response(next_training) if next_training else None,
    )
```

- [ ] **Step 4: `advance_position`**

```python
async def advance_position(session, user, program_id, *, as_skip: bool = False) -> ProgramPositionResponse:
    program = await _load_program_full(...)
    prog = await get_or_create_progress(...)
    state = RotationState(prog.current_slot_index, prog.current_repetition,
                          prog.current_microcycle_number, prog.in_deload)
    new = advance(state, microcycle_length=program.microcycle_length,
                  meso_length=program.mesocycle_length_microcycles,
                  auto_deload=program.auto_deload)
    prog.current_slot_index = new.slot_index
    prog.current_repetition = new.repetition
    prog.current_microcycle_number = new.microcycle_number
    prog.in_deload = new.in_deload
    if not as_skip:
        prog.last_completed_at = _utcnow()
    await session.flush()
    return await get_position(session, user, program_id)
```

(`as_skip` is the hook `05-active-session.md` needs: skip advances the same way but the
progression engine ignores skipped sessions; that engine lives in Plan 06.)

- [ ] **Step 5: `activate_program` / `deactivate_program`**

- `activate_program(user, program_id)`: require **at least one training slot**
  (`any(not s.is_rest_day for s in slots)`), else 422 `"Program needs at least one training slot"`.
  Drop the `len(days) == days_per_week` check entirely (the bug). Deactivate any other active
  program. Call `get_or_create_progress`; if a fresh activation should restart, leave existing
  progress intact per the spec ("re-activation resumes where it left off") — only initialize
  when no progress row exists. Set `is_active=True`, `activated_at=now()`.
- `deactivate_program(user, program_id)`: set `is_active=False`; **leave `program_progress`
  intact**. Remove the old `skip_existing` scheduled-row logic.

- [ ] **Step 6: Delete legacy scheduling (per Decision 2)**

Remove `_generate_schedule_rows`, `extend_continuous_schedule`, `_schedule_anchor`,
`_rederive_future_schedule`, and the `mesocycle_position` week math (was lines ~623-824,
~915-1050). Remove their imports of `compute_mesocycle_position`. Update `update_program` so
a `periodization_mode` flip no longer re-derives a schedule (it only stores the field).
Keep `apply_exercise_deload` (per-lift reactive deload is still valid).

If splitting this PR, gate Step 6 behind a follow-up and leave the legacy functions unused
but compiling.

- [ ] **Step 7: Update existing program-builder tests to new shape**

Edit `tests/test_program_builder_api.py`: `_make_program_payload` drops `weeks`/`days_per_week`;
assertions on `day["day_index"]` become `day["slot_index"]`; add `is_rest_day` where relevant.

- [ ] **Step 8: Run the program test module**

Run: `cd apps/api && uv run pytest tests/test_program_builder_api.py -v`
Expected: all green (after the edits).

- [ ] **Step 9: Commit**

```bash
git add apps/api/app/services/programs.py apps/api/tests/test_program_builder_api.py
git commit -m "feat(api): slot CRUD + rotation position/advance; remove legacy scheduler"
```

---

## Task 7: Duplicate, save-as-template, template visibility

**Files:**
- Modify: `app/services/programs.py`, `app/routers/programs.py`
- Test: `tests/test_program_templates_api.py`

- [ ] **Step 1: Write failing integration tests**

```python
# tests/test_program_templates_api.py  (mirror the _sign_in helper from test_program_builder_api)
async def test_duplicate_creates_independent_fork(client, monkeypatch):
    headers = await _sign_in(client, monkeypatch)
    prog = (await client.post("/v1/programs", headers=headers, json={"name": "Base", "goal": "general"})).json()
    await client.post(f"/v1/programs/{prog['id']}/slots", headers=headers, json={"name": "Push"})
    dup = await client.post(f"/v1/programs/{prog['id']}/duplicate", headers=headers)
    assert dup.status_code == 201
    body = dup.json()["program"]
    assert body["id"] != prog["id"]
    assert body["name"].endswith("(copy)")
    assert body["is_active"] is False
    assert body["template_id"] is None


async def test_save_as_template_then_appears_for_owner(client, monkeypatch):
    headers = await _sign_in(client, monkeypatch)
    prog = (await client.post("/v1/programs", headers=headers, json={"name": "Mine", "goal": "general"})).json()
    await client.post(f"/v1/programs/{prog['id']}/slots", headers=headers, json={"name": "Full body"})
    saved = await client.post(
        f"/v1/programs/{prog['id']}/save-as-template",
        headers=headers, json={"name": "My Template", "visibility": "private"},
    )
    assert saved.status_code == 201
    listing = (await client.get("/v1/program-templates", headers=headers)).json()
    names = [t["name"] for t in listing["items"]]
    assert "My Template" in names


async def test_private_template_hidden_from_other_user(client, monkeypatch):
    h1 = await _sign_in(client, monkeypatch, sub="user-1")
    prog = (await client.post("/v1/programs", headers=h1, json={"name": "P", "goal": "general"})).json()
    await client.post(f"/v1/programs/{prog['id']}/slots", headers=h1, json={"name": "A"})
    await client.post(f"/v1/programs/{prog['id']}/save-as-template", headers=h1,
                      json={"name": "Secret", "visibility": "private"})
    h2 = await _sign_in(client, monkeypatch, sub="user-2")
    listing = (await client.get("/v1/program-templates", headers=h2)).json()
    assert "Secret" not in [t["name"] for t in listing["items"]]
```

- [ ] **Step 2: Run, verify fail**

Run: `cd apps/api && uv run pytest tests/test_program_templates_api.py -v`
Expected: FAIL (endpoints 404 / not implemented)

- [ ] **Step 3: Implement the services**

- `duplicate_program(user, program_id)`: deep-copy the program + its slots + exercise rows
  into a new `Program` (`source="copied"`, `template_id=None`, `name = f"{name} (copy)"`,
  `is_active=False`); fresh (no) progress row. Mirror `copy_template_to_program`'s row-cloning.
- `save_as_template(user, program_id, name, visibility)`: build a `ProgramTemplate` with
  `owner_id=user.id`, `visibility`, `microcycle_length`, `mesocycle_length_microcycles`, and
  `data` in the new **slots** shape (Task 9 shape): `{"slug_map": {...}, "slots": [{"name",
  "is_rest_day", "exercises": [...]}]}`. Reuse the exercise→slug serialization.
- `list_templates(user)`: return curated (`owner_id IS NULL`) + the requester's own
  (`owner_id == user.id`) + all `shared` (`visibility == 'shared'`). Order curated first.

- [ ] **Step 4: Wire the endpoints**

In `app/routers/programs.py`:
```python
@router.post("/programs/{program_id}/duplicate", status_code=201, response_model=DuplicateProgramResponse)
@router.post("/programs/{program_id}/save-as-template", status_code=201, response_model=SaveAsTemplateResponse)
```
Update `GET /program-templates` to pass `user` into `list_templates`.

- [ ] **Step 5: Run, verify pass**

Run: `cd apps/api && uv run pytest tests/test_program_templates_api.py -v`
Expected: 3 passed

- [ ] **Step 6: Commit**

```bash
git add apps/api/app/services/programs.py apps/api/app/routers/programs.py apps/api/tests/test_program_templates_api.py
git commit -m "feat(api): program duplicate, save-as-template, template visibility"
```

---

## Task 8: Wire slot + position + advance + activate endpoints; remove week endpoints

**Files:**
- Modify: `app/routers/programs.py`
- Test: `tests/test_program_slots_api.py`, `tests/test_program_rotation_api.py`

- [ ] **Step 1: Write failing slot tests**

```python
# tests/test_program_slots_api.py
async def test_add_reorder_and_rest_toggle_slots(client, monkeypatch):
    headers = await _sign_in(client, monkeypatch)
    prog = (await client.post("/v1/programs", headers=headers, json={"name": "P", "goal": "general"})).json()
    a = (await client.post(f"/v1/programs/{prog['id']}/slots", headers=headers, json={"name": "Push"})).json()
    b = (await client.post(f"/v1/programs/{prog['id']}/slots", headers=headers, json={"name": "Rest", "is_rest_day": True})).json()
    full = (await client.get(f"/v1/programs/{prog['id']}", headers=headers)).json()
    assert full["microcycle_length"] == 2
    assert [s["slot_index"] for s in full["days"]] == [0, 1]
    assert full["days"][1]["is_rest_day"] is True
    # reorder
    await client.post(f"/v1/programs/{prog['id']}/slots/reorder", headers=headers,
                      json={"slot_ids": [b["id"], a["id"]]})
    full2 = (await client.get(f"/v1/programs/{prog['id']}", headers=headers)).json()
    assert full2["days"][0]["id"] == b["id"]


async def test_activate_requires_one_training_slot(client, monkeypatch):
    headers = await _sign_in(client, monkeypatch)
    prog = (await client.post("/v1/programs", headers=headers, json={"name": "P", "goal": "general"})).json()
    # rest-only -> cannot activate
    await client.post(f"/v1/programs/{prog['id']}/slots", headers=headers, json={"name": "Rest", "is_rest_day": True})
    bad = await client.post(f"/v1/programs/{prog['id']}/activate", headers=headers)
    assert bad.status_code == 422
    # add a training slot -> activates
    await client.post(f"/v1/programs/{prog['id']}/slots", headers=headers, json={"name": "Push"})
    ok = await client.post(f"/v1/programs/{prog['id']}/activate", headers=headers)
    assert ok.status_code == 200
    assert ok.json()["is_active"] is True
```

- [ ] **Step 2: Write failing rotation API test**

```python
# tests/test_program_rotation_api.py
async def test_position_advances_and_wraps(client, monkeypatch):
    headers = await _sign_in(client, monkeypatch)
    prog = (await client.post("/v1/programs", headers=headers, json={"name": "P", "goal": "general"})).json()
    for name, rest in [("Push", False), ("Rest", True), ("Pull", False)]:
        await client.post(f"/v1/programs/{prog['id']}/slots", headers=headers,
                          json={"name": name, "is_rest_day": rest})
    await client.post(f"/v1/programs/{prog['id']}/activate", headers=headers)
    pos = (await client.get(f"/v1/programs/{prog['id']}/position", headers=headers)).json()
    assert pos["current_slot_index"] == 0 and pos["is_rest_day"] is False
    # advance onto the rest slot
    pos = (await client.post(f"/v1/programs/{prog['id']}/advance", headers=headers)).json()
    assert pos["current_slot_index"] == 1 and pos["is_rest_day"] is True
    assert pos["next_training_slot"]["name"] == "Pull"
    # advance to last, then wrap to slot 0 / repetition 2
    await client.post(f"/v1/programs/{prog['id']}/advance", headers=headers)
    pos = (await client.post(f"/v1/programs/{prog['id']}/advance", headers=headers)).json()
    assert pos["current_slot_index"] == 0 and pos["current_repetition"] == 2
```

- [ ] **Step 3: Run, verify fail**

Run: `cd apps/api && uv run pytest tests/test_program_slots_api.py tests/test_program_rotation_api.py -v`
Expected: FAIL (404s)

- [ ] **Step 4: Add the routes**

```python
@router.post("/programs/{program_id}/slots", status_code=201, response_model=ProgramDayResponse)
@router.patch("/program-slots/{slot_id}", response_model=ProgramResponse)
@router.delete("/program-slots/{slot_id}", status_code=204)
@router.post("/programs/{program_id}/slots/reorder", response_model=ProgramResponse)
@router.post("/program-slots/{slot_id}/exercises", status_code=201, response_model=ProgramResponse)  # was /program-days/{day_id}/exercises
@router.get("/programs/{program_id}/position", response_model=ProgramPositionResponse)
@router.post("/programs/{program_id}/advance", response_model=ProgramPositionResponse)  # body: {as_skip?: bool}
@router.post("/programs/{program_id}/activate", response_model=ProgramResponse)  # no body now
@router.post("/programs/{program_id}/deactivate", response_model=ProgramResponse)
```

Remove the old `/programs/{id}/days`, `/program-days/...`, `/programs/{id}/mesocycle`,
`/programs/{id}/trigger-deload`, and the `ActivateRequest`-bodied activate. Keep
`/programs/{id}/exercises/{exercise_id}/deload` (per-lift reactive deload survives).

- [ ] **Step 5: Run, verify pass**

Run: `cd apps/api && uv run pytest tests/test_program_slots_api.py tests/test_program_rotation_api.py -v`
Expected: all passed

- [ ] **Step 6: Commit**

```bash
git add apps/api/app/routers/programs.py apps/api/tests/test_program_slots_api.py apps/api/tests/test_program_rotation_api.py
git commit -m "feat(api): slot, position, advance, activate endpoints"
```

---

## Task 9: Seed DSL + templates to slots shape, reseed

**Files:**
- Modify: `seed/programs/_dsl.py`, `seed/programs/*.py`, `scripts/seed_programs.py`

- [ ] **Step 1: Update the DSL dataclasses**

In `_dsl.py`: rename `Day` usage to slots semantics — add `is_rest_day: bool = False` to the
day/slot dataclass. On `Program`: replace `weeks`/`days_per_week` with `microcycle_length`
(derived from `len(days)`) and `mesocycle_length_microcycles: int = 4`. Update `to_data()` to
emit `{"slug_map": {...}, "slots": [{"name", "is_rest_day", "exercises": [...]}]}` instead of
`"days"`.

- [ ] **Step 2: Update each seed template module**

For each file in `seed/programs/` (arnold_split_6day, bro_split_5day, five_three_one_bbb,
nsuns_531_lp, ppl_6day, push_pull_4day, starting_strength, upper_lower_4day): drop `weeks=`
and `days_per_week=`; insert explicit rest slots where the program implies them so the
microcycle length reflects real cadence (e.g. PPL 6-day becomes 6 training slots + a rest
slot if the author intends a 7-slot week — keep authoring intent, but rest is now explicit).

- [ ] **Step 3: Update `scripts/seed_programs.py`**

Write `microcycle_length` (= slot count), `mesocycle_length_microcycles`, `owner_id=None`,
`visibility=None` (curated). Keep the `ON CONFLICT DO UPDATE` upsert by slug.

- [ ] **Step 4: Run the seeder against the scratch DB**

Run: `cd apps/api && uv run python scripts/seed_programs.py`
Expected: processed N, upserted N, no slug-resolution failure.

- [ ] **Step 5: Commit**

```bash
git add apps/api/seed/programs apps/api/scripts/seed_programs.py
git commit -m "feat(api): reseed templates in microcycle slots shape"
```

---

## Task 10: Update data-model.md, regenerate OpenAPI + web types, full suite

**Files:**
- Modify: `tasks/00-overview/data-model.md`
- Regenerate: `packages/openapi/openapi.json`, `apps/web/src/lib/api/types.ts`

- [ ] **Step 1: Update `data-model.md`**

Reflect: programs (microcycle_length, mesocycle_length_microcycles, no weeks/days_per_week),
program_days (slot_index, is_rest_day), program_templates (owner_id, visibility,
microcycle_length, mesocycle_length_microcycles, slots data shape), scheduled_workouts
(microcycle_number, repetition, nullable scheduled_for), and the new `program_progress` table
+ `template_visibility` enum.

- [ ] **Step 2: Regenerate the OpenAPI contract**

Run (per memory: always use the export script, never inline json):
`cd apps/api && uv run python scripts/export_openapi.py`
Then: `cd apps/web && pnpm openapi:generate`
Expected: `openapi.json` and `types.ts` updated; CI key-sort clean.

- [ ] **Step 3: Run the whole API suite**

Run: `cd apps/api && uv run pytest -q`
Expected: all pass.

- [ ] **Step 4: Check OpenAPI drift gate**

Run the repo's drift check (per memory `reference_gym_app_commands.md`). Expected: no drift.

- [ ] **Step 5: Commit**

```bash
git add tasks/00-overview/data-model.md packages/openapi/openapi.json apps/web/src/lib/api/types.ts
git commit -m "chore: regenerate OpenAPI + web types for flexible program model"
```

---

## Self-review

**Spec coverage (`01-program-model.md`):**
- §2 schema changes → Tasks 2, 3 (programs, program_days, program_templates,
  scheduled_workouts, program_progress). ✓
- §3 migration backfill order → Task 3 (add nullable → backfill → non-null → drop). ✓
- §4 API (create empty, slot endpoints, activate/deactivate, position, from-template copy,
  duplicate, save-as-template, template list visibility) → Tasks 6, 7, 8. ✓ (`from-template`
  copy already exists as `copy_template_to_program`; Task 9 keeps it working with the slots
  shape — **add a test** that copying a curated template yields slots.)
- §5 validation (≥1 training slot, meso ≥ 1, microcycle_length = slot count) → Task 6/8. ✓
- §6 acceptance → covered by Tasks 6–10 tests.

**Gap found in review:** add to Task 7 a test that `POST /program-templates/{slug}/copy`
produces a program whose `days` carry `slot_index`/`is_rest_day` from `data.slots`. Add it.

**Placeholder scan:** the `server_default=...` in Task 1 Step 3 is intentionally "copy from
sibling model" — the implementer must paste the real expression; called out explicitly, not a
silent TODO.

**Type consistency:** `microcycle_length`, `mesocycle_length_microcycles`, `slot_index`,
`is_rest_day`, `current_slot_index`, `current_repetition`, `current_microcycle_number`,
`in_deload` used identically across models, schemas, and tests. `advance(...)` signature
matches between `rotation.py` and its callers in `programs.py`.

---

## Roadmap: Plans 2 and 3 (detailed after this lands)

These are the design-heavy plans your instructions target. They depend on the regenerated web
types from Task 10 and will be authored with the **frontend-design** and **motion** skills
driving the actual screen/animation design.

### Plan 2 — Responsive + motion foundation (cross-cutting, web)

Built once, consumed by every surface. Establishes the patterns on Programs first.

- **Breakpoint tokens.** Add a Tailwind v4 `@theme` breakpoint set beyond the lone `md`:
  `sm 640 / md 768 / lg 1024 / xl 1280`, plus explicit **tablet/mid-window** handling — the
  current hard sidebar(≥768)/tabbar(<768) split has nothing in between. Define a fluid type
  and spacing scale with `clamp()` so the "cramped at wide viewports" bug (`02 §1`) is fixed
  structurally, not per-page.
- **Motion install + primitives.** Add `motion` (`motion/react`). The token file already
  defines `--motion-fast/base/slow` springs (unused today) — wire primitives to them: a
  `<Motion>`/`<FadeIn>`/`<Pressable>` set, `AnimatePresence` page/sheet transitions, and a
  shared `useReducedMotionSafe` wrapper so every animation honors `prefers-reduced-motion`
  (only `rest-timer.tsx` does today). Restrained & physical: <200ms, spring, no decorative
  motion — consistent with the editorial language.
- **Layout shell.** Update `desktop-sidebar.tsx`, `mobile-tabbar.tsx`, `top-bar.tsx` to the
  new breakpoints and a fluid content max-width.

### Plan 3 — Programs web UI on the new model (web)

Rebinds the 16 program components from the old shape to the new types and applies the
responsive + motion foundation. Per `02-programs-screens.md`:

- **Data rebind:** every `weeks`/`days_per_week`/`day_index`/`mesocycle_length_weeks`
  reference (browse-templates, template-detail, program-masthead, program-library,
  program-builder, mesocycle-bar, week-list, per-day-detail, today-card) → microcycle/slot
  fields. `programs/new/page.tsx` loses the hard-coded `weeks:6, days_per_week:4`.
- **New-program chooser** (`onboarding.tsx`) becomes the entry point for *every* create, not
  first-run only.
- **Builder:** day rail → draggable **slot rail** with rest toggle (motion: drag-reorder),
  live "N-slot microcycle", mesocycle-length control + auto-deload toggle on periodization,
  activation enabled on ≥1 training slot.
- **Cycle bar:** weeks → microcycle repetitions + trailing deload cell.
- **Library:** activate / hover-or-overflow deactivate, duplicate, save-as-template dialog.
- **Spine masthead/today/microcycle list** rebound to `GET /programs/{id}/position`.
- Verified light/dark at phone, **tablet/mid-window**, and desktop.

Then **Programs iOS** follows (per your "per-surface, after web" choice), porting the settled
web shape into `apps/ios/GymApp/Features/Programs` against the existing `Core/Design` system.
(Note: investigate the duplicate `Core 2/`, `Features 2/`, `Programs 2/` folders before iOS
work — likely stray copies to remove.)
```