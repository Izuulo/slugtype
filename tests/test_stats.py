"""Tests for slugtype.stats — pure stat formulas over finalized state."""
from slugtype import stats
from slugtype.input import Key, KeyKind
from slugtype.state import apply_keypress, initial_state


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
