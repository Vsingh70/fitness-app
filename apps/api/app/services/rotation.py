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
            slot_index=0,
            repetition=1,
            microcycle_number=state.microcycle_number + 1,
            in_deload=False,
        )

    return replace(state, slot_index=0, repetition=state.repetition + 1)
