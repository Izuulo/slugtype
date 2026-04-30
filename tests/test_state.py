"""Tests for slugtype.state — pure TestState transitions."""
from slugtype.state import (
    TestState,
    TypedChar,
    WordEntry,
    initial_state,
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
