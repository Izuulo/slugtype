"""Pure TestState dataclass and transitions. No I/O."""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Literal

from slugtype.input import Key

Category = Literal["correct", "incorrect", "extra"]
Mode = Literal["time", "words"]


@dataclass(frozen=True)
class TypedChar:
    expected: str
    typed: str
    category: Category


@dataclass(frozen=True)
class WordEntry:
    expected: str
    typed: tuple[TypedChar, ...]
    submitted: bool


@dataclass(frozen=True)
class TestState:
    words: tuple[WordEntry, ...]
    current_index: int
    started_at: float | None
    ended_at: float | None
    duration_s: float
    mode: Mode
    finished: bool


def initial_state(words: tuple[str, ...], mode: Mode, duration_s: float) -> TestState:
    return TestState(
        words=tuple(WordEntry(expected=w, typed=(), submitted=False) for w in words),
        current_index=0,
        started_at=None,
        ended_at=None,
        duration_s=duration_s,
        mode=mode,
        finished=False,
    )
