"""Tests for slugtype.state — pure TestState transitions."""
from dataclasses import replace

from slugtype.input import Key, KeyKind
from slugtype.state import (
    TestState,
    TypedChar,
    WordEntry,
    initial_state,
    apply_keypress,
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
