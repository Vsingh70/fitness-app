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
    s = advance(
        _state(slot_index=3, repetition=3), microcycle_length=4, meso_length=3, auto_deload=True
    )
    assert s.in_deload is True
    assert (s.slot_index, s.repetition) == (0, 3)


def test_leave_deload_into_next_mesocycle():
    s = advance(
        _state(slot_index=3, repetition=3, in_deload=True),
        microcycle_length=4,
        meso_length=3,
        auto_deload=True,
    )
    assert s.in_deload is False
    assert (s.slot_index, s.repetition, s.microcycle_number) == (0, 1, 2)


def test_no_deload_rolls_straight_into_next_meso():
    s = advance(
        _state(slot_index=3, repetition=3), microcycle_length=4, meso_length=3, auto_deload=False
    )
    assert s.in_deload is False
    assert (s.slot_index, s.repetition, s.microcycle_number) == (0, 1, 2)
