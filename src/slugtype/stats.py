"""Pure stat functions over a TestState. No I/O."""
from __future__ import annotations

import math
from dataclasses import dataclass

from slugtype.state import TestState, WordEntry


def correct_chars(state: TestState) -> int:
    return sum(1 for w in state.words for tc in w.typed if tc.category == "correct")


def incorrect_chars(state: TestState) -> int:
    return sum(1 for w in state.words for tc in w.typed if tc.category == "incorrect")


def extra_chars(state: TestState) -> int:
    return sum(1 for w in state.words for tc in w.typed if tc.category == "extra")


def accuracy(state: TestState) -> float:
    correct = correct_chars(state)
    incorrect = incorrect_chars(state)
    total = correct + incorrect
    if total == 0:
        return 100.0
    return 100.0 * correct / total


@dataclass(frozen=True)
class Summary:
    wpm: float
    raw_wpm: float
    accuracy: float
    correct_chars: int
    incorrect_chars: int
    extra_chars: int


def _is_fully_correct(word: WordEntry) -> bool:
    if not word.submitted:
        return False
    if len(word.typed) != len(word.expected):
        return False
    return all(tc.category == "correct" for tc in word.typed)


def _test_seconds(state: TestState) -> float:
    if state.started_at is None or state.ended_at is None:
        return 0.0
    return state.ended_at - state.started_at


def wpm(state: TestState) -> float:
    seconds = _test_seconds(state)
    if seconds <= 0:
        return 0.0
    fully_correct = [_is_fully_correct(w) for w in state.words]
    correct_word_chars = sum(
        len(w.expected) for w, ok in zip(state.words, fully_correct) if ok
    )
    correct_spaces = 0
    for i in range(len(fully_correct) - 1):
        if fully_correct[i] and fully_correct[i + 1]:
            correct_spaces += 1
    return (correct_word_chars + correct_spaces) * 60.0 / seconds / 5.0


def raw_wpm(state: TestState) -> float:
    seconds = _test_seconds(state)
    if seconds <= 0:
        return 0.0
    typed_chars = sum(len(w.typed) for w in state.words)
    submitted_spaces = sum(1 for w in state.words if w.submitted)
    return (typed_chars + submitted_spaces) * 60.0 / seconds / 5.0


def summary(state: TestState) -> Summary:
    return Summary(
        wpm=wpm(state),
        raw_wpm=raw_wpm(state),
        accuracy=accuracy(state),
        correct_chars=correct_chars(state),
        incorrect_chars=incorrect_chars(state),
        extra_chars=extra_chars(state),
    )


def consistency(state: TestState) -> float:
    """Kogasa consistency: 100 * (1 - tanh(cv + cv³/3)) where cv = stdev/mean
    over the per-second raw-WPM samples.
    Returns 100.0 when there are fewer than 2 samples or the mean is 0.
    """
    samples = state.raw_per_second
    if len(samples) < 2:
        return 100.0
    mean = sum(samples) / len(samples)
    if mean == 0:
        return 100.0
    variance = sum((x - mean) ** 2 for x in samples) / len(samples)
    stdev = math.sqrt(variance)
    cv = stdev / mean
    return 100.0 * (1 - math.tanh(cv + (cv ** 3) / 3))


def live_wpm(state: TestState, now: float) -> float:
    """Current WPM using elapsed = now - started_at as the denominator.
    Same fully-correct-word logic as wpm(). Returns 0.0 if not started.
    """
    if state.started_at is None:
        return 0.0
    elapsed = now - state.started_at
    if elapsed <= 0:
        return 0.0
    fully_correct = [_is_fully_correct(w) for w in state.words]
    correct_word_chars = sum(
        len(w.expected) for w, ok in zip(state.words, fully_correct) if ok
    )
    correct_spaces = 0
    for i in range(len(fully_correct) - 1):
        if fully_correct[i] and fully_correct[i + 1]:
            correct_spaces += 1
    return (correct_word_chars + correct_spaces) * 60.0 / elapsed / 5.0
