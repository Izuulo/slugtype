"""Tests for slugtype.history — JSONL persistence and PB queries."""
from dataclasses import dataclass, replace
from datetime import datetime, timezone

import pytest

from slugtype import history
from slugtype.run import Config
from slugtype.state import TestState, WordEntry, TypedChar
from slugtype.stats import Summary


def _finished_state(duration: float = 60.0, samples=()) -> TestState:
    """Build a minimal finished TestState for record_from_state tests."""
    return TestState(
        words=(WordEntry(expected="the", typed=(TypedChar("t", "t", "correct"),), submitted=True),),
        current_index=0,
        started_at=0.0,
        ended_at=duration,
        duration_s=duration,
        mode="time",
        finished=True,
        raw_per_second=tuple(samples),
    )


def _summary(wpm=80.0, acc=95.0) -> Summary:
    return Summary(
        wpm=wpm, raw_wpm=wpm + 5, accuracy=acc, consistency=70.0,
        correct_chars=400, incorrect_chars=20, extra_chars=5,
    )


def _config(mode="time", duration=60, words=0, lang="english-1k") -> Config:
    return Config(
        mode=mode,
        duration_s=float(duration),
        word_count=words,
        language=lang,
        show_live_wpm=True,
    )


def test_record_from_state_populates_all_fields():
    state = _finished_state(duration=60.0, samples=(40.0, 50.0, 60.0))
    summary = _summary(wpm=80.0, acc=96.5)
    config = _config(mode="time", duration=60, lang="english-1k")
    ts = datetime(2026, 5, 7, 19, 14, 2, tzinfo=timezone.utc)

    rec = history.record_from_state(state, summary, config, ts)

    assert rec.ts == "2026-05-07T19:14:02Z"
    assert rec.wpm == 80.0
    assert rec.raw == 85.0
    assert rec.acc == 96.5
    assert rec.consistency == 70.0
    assert rec.mode == "time"
    assert rec.length == 60
    assert rec.language == "english-1k"
    assert rec.punctuation is False
    assert rec.numbers is False
    assert rec.chars == {"correct": 400, "incorrect": 20, "extra": 5, "missed": 0}
    assert rec.duration_s == 60.0
    assert rec.samples == (40.0, 50.0, 60.0)


def test_record_length_uses_word_count_for_words_mode():
    state = _finished_state(duration=12.0)
    summary = _summary()
    config = _config(mode="words", duration=0, words=25, lang="english-200")

    rec = history.record_from_state(state, summary, config, datetime(2026, 5, 7, tzinfo=timezone.utc))

    assert rec.mode == "words"
    assert rec.length == 25
