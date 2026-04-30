"""Tests for slugtype.stats — pure stat formulas over finalized state."""
import math

from dataclasses import replace

from slugtype import stats
from slugtype.input import Key, KeyKind
from slugtype.state import apply_keypress, initial_state, tick


def _char(c: str) -> Key:
    return Key(kind=KeyKind.CHAR, char=c)


def _space() -> Key:
    return Key(kind=KeyKind.SPACE)


def _type_words(s, sequence, now=1.0):
    """Helper: feed a key sequence describing whole-word typing.

    sequence is a list of (word, submit) tuples — `word` is the chars to type,
    `submit` is whether to send a space after.
    """
    for word, submit in sequence:
        for c in word:
            s = apply_keypress(s, _char(c), now=now)
        if submit:
            s = apply_keypress(s, _space(), now=now)
    return s


def test_correct_chars_counts_only_correct_typed_chars():
    s = initial_state(("the", "and"), "time", 60.0)
    s = _type_words(s, [("the", True), ("axd", False)])
    assert stats.correct_chars(s) == 5   # t,h,e,a,d
    assert stats.incorrect_chars(s) == 1  # x


def test_extra_chars_count_typed_past_word_length():
    s = initial_state(("the",), "time", 60.0)
    s = _type_words(s, [("thexx", False)])
    assert stats.extra_chars(s) == 2


def test_accuracy_all_correct_is_100():
    s = initial_state(("the",), "time", 60.0)
    s = _type_words(s, [("the", False)])
    assert stats.accuracy(s) == 100.0


def test_accuracy_all_incorrect_is_zero():
    s = initial_state(("the",), "time", 60.0)
    s = _type_words(s, [("xxx", False)])
    assert stats.accuracy(s) == 0.0


def test_accuracy_half_half():
    s = initial_state(("abcd",), "time", 60.0)
    for c in "axcy":
        s = apply_keypress(s, _char(c), now=1.0)
    assert stats.accuracy(s) == 50.0


def test_accuracy_empty_state_is_100():
    s = initial_state(("the",), "time", 60.0)
    assert stats.accuracy(s) == 100.0


def _finalize_time_mode(s, started_at, duration_s):
    """Helper: apply time-mode finish to a state for stat tests."""
    return replace(
        s,
        started_at=started_at,
        ended_at=started_at + duration_s,
        finished=True,
    )


def test_wpm_zero_when_no_words_submitted():
    s = initial_state(("the",), "time", 60.0)
    for c in "th":  # typed but not submitted
        s = apply_keypress(s, _char(c), now=1.0)
    s = _finalize_time_mode(s, started_at=1.0, duration_s=60.0)
    assert stats.wpm(s) == 0.0


def test_wpm_zero_when_started_at_is_none():
    s = initial_state(("the",), "time", 60.0)
    assert stats.wpm(s) == 0.0


def test_wpm_one_correct_word_60s():
    s = initial_state(("the", "and"), "time", 60.0)
    s = _type_words(s, [("the", True)])
    s = _finalize_time_mode(s, started_at=1.0, duration_s=60.0)
    # correct_word_chars=3 ("the"), correct_spaces=0
    # wpm = (3 + 0) * 60 / 60 / 5 = 0.6
    assert math.isclose(stats.wpm(s), 0.6)


def test_wpm_two_correct_words_60s():
    s = initial_state(("the", "and", "go"), "time", 60.0)
    s = _type_words(s, [("the", True), ("and", True)])
    s = _finalize_time_mode(s, started_at=1.0, duration_s=60.0)
    # correct_word_chars=6, correct_spaces=1
    # wpm = (6 + 1) * 60 / 60 / 5 = 1.4
    assert math.isclose(stats.wpm(s), 1.4)


def test_wpm_incorrect_word_breaks_correct_spaces_chain():
    s = initial_state(("the", "and", "go"), "time", 60.0)
    s = _type_words(s, [("the", True), ("axd", True), ("go", True)])
    s = _finalize_time_mode(s, started_at=1.0, duration_s=60.0)
    # correct_word_chars = 3 + 2 = 5, correct_spaces = 0
    # wpm = (5 + 0) * 60 / 60 / 5 = 1.0
    assert math.isclose(stats.wpm(s), 1.0)


def test_wpm_extras_disqualify_a_word():
    s = initial_state(("the", "and"), "time", 60.0)
    s = _type_words(s, [("thee", True), ("and", True)])
    # "thee" has 3 correct + 1 extra → not fully correct
    s = _finalize_time_mode(s, started_at=1.0, duration_s=60.0)
    assert math.isclose(stats.wpm(s), (3 + 0) * 60 / 60 / 5)


def test_raw_wpm_counts_all_typed_chars_plus_submitted_spaces():
    s = initial_state(("the", "and"), "time", 60.0)
    s = _type_words(s, [("thee", True), ("and", True)])
    # typed: 4 + 3 = 7 chars; submitted spaces = 2
    # raw = (7 + 2) * 60 / 60 / 5 = 1.8
    s = _finalize_time_mode(s, started_at=1.0, duration_s=60.0)
    assert math.isclose(stats.raw_wpm(s), 1.8)


def test_summary_returns_all_fields():
    s = initial_state(("the", "and"), "time", 60.0)
    s = _type_words(s, [("the", True), ("and", True)])
    s = _finalize_time_mode(s, started_at=1.0, duration_s=60.0)
    summary = stats.summary(s)
    assert math.isclose(summary.wpm, 1.4)
    assert math.isclose(summary.raw_wpm, (6 + 2) * 60 / 60 / 5)
    assert summary.accuracy == 100.0
    assert summary.correct_chars == 6
    assert summary.incorrect_chars == 0
    assert summary.extra_chars == 0
