"""Tests for slugtype.state — pure TestState transitions."""
from dataclasses import replace

from slugtype.input import Key, KeyKind
from slugtype.state import (
    TestState,
    TypedChar,
    WordEntry,
    initial_state,
    apply_keypress,
    apply_pause_offset,
    _word_was_perfect,
)


def test_initial_state_time_mode():
    s = initial_state(words=("the", "and"), mode="time", duration_s=60.0)
    assert s.mode == "time"
    assert s.duration_s == 60.0
    assert s.current_index == 0
    assert s.started_at is None
    assert s.ended_at is None
    assert s.finished is False
    assert len(s.words) == 2
    assert s.words[0].expected == "the"
    assert s.words[0].typed == ()
    assert s.words[0].submitted is False
    assert s.words[1].expected == "and"


def test_initial_state_words_mode():
    s = initial_state(words=("the",), mode="words", duration_s=0.0)
    assert s.mode == "words"
    assert s.finished is False
    assert s.words[0].expected == "the"


def _char(c: str) -> Key:
    return Key(kind=KeyKind.CHAR, char=c)


def test_first_char_starts_the_clock():
    s = initial_state(("the",), "time", 60.0)
    s2 = apply_keypress(s, _char("t"), now=100.0)
    assert s2.started_at == 100.0
    assert s2.words[0].typed == (TypedChar("t", "t", "correct"),)


def test_correct_char_appends_correct_typed_char():
    s = initial_state(("the",), "time", 60.0)
    s = apply_keypress(s, _char("t"), now=1.0)
    s = apply_keypress(s, _char("h"), now=1.5)
    assert s.words[0].typed == (
        TypedChar("t", "t", "correct"),
        TypedChar("h", "h", "correct"),
    )


def test_incorrect_char_appends_incorrect_typed_char():
    s = initial_state(("the",), "time", 60.0)
    s = apply_keypress(s, _char("x"), now=1.0)
    assert s.words[0].typed == (TypedChar("t", "x", "incorrect"),)


def test_extra_char_past_word_length_marked_extra():
    s = initial_state(("the",), "time", 60.0)
    for c in "thex":
        s = apply_keypress(s, _char(c), now=1.0)
    assert s.words[0].typed == (
        TypedChar("t", "t", "correct"),
        TypedChar("h", "h", "correct"),
        TypedChar("e", "e", "correct"),
        TypedChar("", "x", "extra"),
    )


def test_char_after_finished_is_noop():
    s = initial_state(("the",), "time", 60.0)
    s = replace(s, finished=True, ended_at=1.0)
    s2 = apply_keypress(s, _char("t"), now=2.0)
    assert s2 is s


def _space() -> Key:
    return Key(kind=KeyKind.SPACE)


def test_space_at_word_start_is_noop():
    s = initial_state(("the", "and"), "time", 60.0)
    s2 = apply_keypress(s, _space(), now=1.0)
    assert s2 is s


def test_space_after_chars_submits_word_and_advances():
    s = initial_state(("the", "and"), "time", 60.0)
    for c in "the":
        s = apply_keypress(s, _char(c), now=1.0)
    s = apply_keypress(s, _space(), now=2.0)
    assert s.words[0].submitted is True
    assert s.current_index == 1
    assert s.finished is False


def test_space_on_last_word_in_words_mode_finishes_test():
    s = initial_state(("the",), "words", duration_s=0.0)
    for c in "the":
        s = apply_keypress(s, _char(c), now=1.0)
    s = apply_keypress(s, _space(), now=2.5)
    assert s.finished is True
    assert s.ended_at == 2.5
    assert s.words[0].submitted is True
    # current_index does not advance past the last word
    assert s.current_index == 0


def test_space_on_last_word_in_time_mode_does_not_finish():
    s = initial_state(("the",), "time", duration_s=60.0)
    for c in "the":
        s = apply_keypress(s, _char(c), now=1.0)
    s = apply_keypress(s, _space(), now=2.5)
    assert s.finished is False
    assert s.ended_at is None


def _backspace() -> Key:
    return Key(kind=KeyKind.BACKSPACE)


def test_backspace_pops_one_typed_char():
    s = initial_state(("the",), "time", 60.0)
    for c in "th":
        s = apply_keypress(s, _char(c), now=1.0)
    s = apply_keypress(s, _backspace(), now=2.0)
    assert s.words[0].typed == (TypedChar("t", "t", "correct"),)


def test_backspace_at_word_start_is_noop():
    s = initial_state(("the",), "time", 60.0)
    s2 = apply_keypress(s, _backspace(), now=1.0)
    assert s2 is s


def test_backspace_does_not_cross_word_boundary():
    s = initial_state(("the", "and"), "time", 60.0)
    for c in "the":
        s = apply_keypress(s, _char(c), now=1.0)
    s = apply_keypress(s, _space(), now=2.0)
    # Now on word 1 with no typed chars — backspace must be no-op, not jump back
    s2 = apply_keypress(s, _backspace(), now=2.5)
    assert s2.current_index == 1
    assert s2.words[0].submitted is True
    assert s2.words[0].typed == (
        TypedChar("t", "t", "correct"),
        TypedChar("h", "h", "correct"),
        TypedChar("e", "e", "correct"),
    )


def test_backspace_does_not_set_started_at():
    s = initial_state(("the",), "time", 60.0)
    s2 = apply_keypress(s, _backspace(), now=5.0)
    assert s2.started_at is None


from slugtype.state import tick


def test_tick_in_time_mode_finishes_when_duration_elapsed():
    s = initial_state(("the",), "time", duration_s=10.0)
    s = apply_keypress(s, _char("t"), now=100.0)
    s = tick(s, now=110.0)
    assert s.finished is True
    assert s.ended_at == 110.0


def test_tick_in_time_mode_does_not_finish_before_duration():
    s = initial_state(("the",), "time", duration_s=10.0)
    s = apply_keypress(s, _char("t"), now=100.0)
    s = tick(s, now=105.0)
    assert s.finished is False


def test_tick_in_time_mode_with_no_started_at_is_noop():
    s = initial_state(("the",), "time", duration_s=10.0)
    s2 = tick(s, now=200.0)
    assert s2 is s


def test_tick_in_words_mode_is_noop():
    s = initial_state(("the",), "words", duration_s=0.0)
    s = apply_keypress(s, _char("t"), now=1.0)
    s2 = tick(s, now=999.0)
    assert s2.finished is False


def test_initial_state_has_empty_raw_per_second():
    s = initial_state(("the",), "time", 60.0)
    assert s.raw_per_second == ()


from slugtype.state import append_sample


def test_append_sample_returns_new_state_with_sample_appended():
    s = initial_state(("the",), "time", 60.0)
    s2 = append_sample(s, 42.0)
    assert s2.raw_per_second == (42.0,)
    s3 = append_sample(s2, 50.0)
    assert s3.raw_per_second == (42.0, 50.0)
    # Original states are unmodified.
    assert s.raw_per_second == ()
    assert s2.raw_per_second == (42.0,)


def test_word_was_perfect_all_correct():
    word = WordEntry(
        expected="the",
        typed=(
            TypedChar("t", "t", "correct"),
            TypedChar("h", "h", "correct"),
            TypedChar("e", "e", "correct"),
        ),
        submitted=True,
    )
    assert _word_was_perfect(word) is True


def test_word_was_perfect_has_incorrect():
    word = WordEntry(
        expected="the",
        typed=(
            TypedChar("t", "t", "correct"),
            TypedChar("h", "x", "incorrect"),
            TypedChar("e", "e", "correct"),
        ),
        submitted=True,
    )
    assert _word_was_perfect(word) is False


def test_word_was_perfect_has_extra():
    word = WordEntry(
        expected="the",
        typed=(
            TypedChar("t", "t", "correct"),
            TypedChar("h", "h", "correct"),
            TypedChar("e", "e", "correct"),
            TypedChar("", "x", "extra"),
        ),
        submitted=True,
    )
    assert _word_was_perfect(word) is False


def test_word_was_perfect_missed_chars():
    word = WordEntry(
        expected="the",
        typed=(TypedChar("t", "t", "correct"),),
        submitted=True,
    )
    assert _word_was_perfect(word) is False


def test_word_was_perfect_empty_typed():
    word = WordEntry(expected="the", typed=(), submitted=True)
    assert _word_was_perfect(word) is False


def test_backspace_within_word_unchanged():
    """Existing in-word behavior preserved: backspace removes one char."""
    s = initial_state(("the",), "time", 60.0)
    s = apply_keypress(s, _char("t"), now=1.0)
    s = apply_keypress(s, _char("h"), now=1.0)
    s = apply_keypress(s, Key(kind=KeyKind.BACKSPACE), now=2.0)
    assert s.words[0].typed == (TypedChar("t", "t", "correct"),)


def test_backspace_at_word_zero_empty_buffer_noop():
    s = initial_state(("the", "and"), "time", 60.0)
    s2 = apply_keypress(s, Key(kind=KeyKind.BACKSPACE), now=1.0)
    assert s2 is s


def test_backspace_does_not_cross_perfect_previous_word():
    """Type 'the' exactly + space + (now on 'and' with empty buffer)
    + backspace → caret stays on 'and', 'the' stays submitted."""
    s = initial_state(("the", "and"), "time", 60.0)
    for ch in "the":
        s = apply_keypress(s, _char(ch), now=1.0)
    s = apply_keypress(s, Key(kind=KeyKind.SPACE), now=1.5)
    assert s.current_index == 1
    s_after = apply_keypress(s, Key(kind=KeyKind.BACKSPACE), now=2.0)
    assert s_after is s


def test_backspace_crosses_into_imperfect_previous_word():
    """Type 'thx' (one wrong) + space + backspace → caret jumps back into
    word 0, which is no longer submitted."""
    s = initial_state(("the", "and"), "time", 60.0)
    for ch in "thx":
        s = apply_keypress(s, _char(ch), now=1.0)
    s = apply_keypress(s, Key(kind=KeyKind.SPACE), now=1.5)
    assert s.current_index == 1
    assert s.words[0].submitted is True

    s_after = apply_keypress(s, Key(kind=KeyKind.BACKSPACE), now=2.0)
    assert s_after.current_index == 0
    assert s_after.words[0].submitted is False
    # The typed buffer is preserved; user's next backspace edits it.
    assert s_after.words[0].typed == s.words[0].typed


def test_backspace_crosses_into_word_with_missed_chars():
    """Type 'th' (only 2 of 3) + space + backspace → caret jumps back."""
    s = initial_state(("the", "and"), "time", 60.0)
    for ch in "th":
        s = apply_keypress(s, _char(ch), now=1.0)
    s = apply_keypress(s, Key(kind=KeyKind.SPACE), now=1.5)
    assert s.current_index == 1

    s_after = apply_keypress(s, Key(kind=KeyKind.BACKSPACE), now=2.0)
    assert s_after.current_index == 0
    assert s_after.words[0].submitted is False


def test_backspace_after_crossing_then_deletes_last_typed_char():
    """After crossing back, the next backspace edits the previous word."""
    s = initial_state(("the", "and"), "time", 60.0)
    for ch in "thx":
        s = apply_keypress(s, _char(ch), now=1.0)
    s = apply_keypress(s, Key(kind=KeyKind.SPACE), now=1.5)
    s = apply_keypress(s, Key(kind=KeyKind.BACKSPACE), now=2.0)  # crosses
    # Second backspace should now trim the last typed char of word 0.
    s = apply_keypress(s, Key(kind=KeyKind.BACKSPACE), now=2.5)
    assert s.current_index == 0
    assert s.words[0].typed == (
        TypedChar("t", "t", "correct"),
        TypedChar("h", "h", "correct"),
    )


def test_apply_pause_offset_shifts_started_at_forward():
    s = initial_state(words=("the",), mode="time", duration_s=60.0)
    s = replace(s, started_at=100.0)
    out = apply_pause_offset(s, pause_seconds=3.5)
    assert out.started_at == 103.5
    # Everything else is preserved
    assert out.duration_s == 60.0
    assert out.mode == "time"
    assert out.ended_at is None
    assert out.finished is False
    assert out.words == s.words


def test_apply_pause_offset_no_op_when_not_started():
    s = initial_state(words=("the",), mode="time", duration_s=60.0)
    assert s.started_at is None
    out = apply_pause_offset(s, pause_seconds=5.0)
    assert out is s  # same identity — no replace call


def test_apply_pause_offset_no_op_when_finished():
    s = initial_state(words=("the",), mode="time", duration_s=60.0)
    s = replace(s, started_at=100.0, ended_at=160.0, finished=True)
    out = apply_pause_offset(s, pause_seconds=5.0)
    assert out is s
