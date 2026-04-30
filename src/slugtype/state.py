"""Pure TestState dataclass and transitions. No I/O."""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Literal

from slugtype.input import Key, KeyKind

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
    raw_per_second: tuple[float, ...] = ()


def initial_state(words: tuple[str, ...], mode: Mode, duration_s: float) -> TestState:
    return TestState(
        words=tuple(WordEntry(expected=w, typed=(), submitted=False) for w in words),
        current_index=0,
        started_at=None,
        ended_at=None,
        duration_s=duration_s,
        mode=mode,
        finished=False,
        raw_per_second=(),
    )


def apply_keypress(state: TestState, key: Key, now: float) -> TestState:
    if state.finished:
        return state
    if key.kind is KeyKind.CHAR:
        return _apply_char(state, key.char, now)
    if key.kind is KeyKind.SPACE:
        return _apply_space(state, now)
    if key.kind is KeyKind.BACKSPACE:
        return _apply_backspace(state)
    return state


def _apply_char(state: TestState, ch: str, now: float) -> TestState:
    started_at = state.started_at if state.started_at is not None else now
    current = state.words[state.current_index]
    typed_index = len(current.typed)
    expected = current.expected
    if typed_index < len(expected):
        if ch == expected[typed_index]:
            entry = TypedChar(expected[typed_index], ch, "correct")
        else:
            entry = TypedChar(expected[typed_index], ch, "incorrect")
    else:
        entry = TypedChar("", ch, "extra")
    new_word = WordEntry(
        expected=current.expected,
        typed=current.typed + (entry,),
        submitted=current.submitted,
    )
    new_words = state.words[: state.current_index] + (new_word,) + state.words[state.current_index + 1 :]
    return replace(state, words=new_words, started_at=started_at)


def _apply_space(state: TestState, now: float) -> TestState:
    current = state.words[state.current_index]
    if len(current.typed) == 0:
        return state  # no-op at word start
    new_word = WordEntry(
        expected=current.expected,
        typed=current.typed,
        submitted=True,
    )
    new_words = state.words[: state.current_index] + (new_word,) + state.words[state.current_index + 1 :]
    is_last = state.current_index == len(state.words) - 1
    if is_last and state.mode == "words":
        return replace(state, words=new_words, finished=True, ended_at=now)
    if is_last:
        # In time mode, last word submitted — but timer still controls end. Stay on last index.
        return replace(state, words=new_words)
    return replace(state, words=new_words, current_index=state.current_index + 1)


def _apply_backspace(state: TestState) -> TestState:
    current = state.words[state.current_index]
    if len(current.typed) == 0:
        return state
    new_word = WordEntry(
        expected=current.expected,
        typed=current.typed[:-1],
        submitted=current.submitted,
    )
    new_words = state.words[: state.current_index] + (new_word,) + state.words[state.current_index + 1 :]
    return replace(state, words=new_words)


def tick(state: TestState, now: float) -> TestState:
    if state.finished:
        return state
    if state.mode != "time":
        return state
    if state.started_at is None:
        return state
    if now - state.started_at >= state.duration_s:
        return replace(state, finished=True, ended_at=now)
    return state
