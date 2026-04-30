"""Pure stat functions over a TestState. No I/O."""
from __future__ import annotations

from slugtype.state import TestState


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
