"""Tests for slugtype.input — curses keycode → Key translation."""
import curses

from slugtype.input import Key, KeyKind, translate


def test_translate_letter_returns_char():
    k = translate(ord("a"))
    assert k.kind is KeyKind.CHAR
    assert k.char == "a"


def test_translate_uppercase_letter_returns_char():
    k = translate(ord("Z"))
    assert k.kind is KeyKind.CHAR
    assert k.char == "Z"


def test_translate_space_returns_space():
    assert translate(ord(" ")).kind is KeyKind.SPACE


def test_translate_backspace_codes_return_backspace():
    # curses delivers backspace as one of several codes depending on terminal
    assert translate(curses.KEY_BACKSPACE).kind is KeyKind.BACKSPACE
    assert translate(127).kind is KeyKind.BACKSPACE  # DEL
    assert translate(8).kind is KeyKind.BACKSPACE   # BS


def test_translate_ctrl_c_returns_ctrl_c():
    assert translate(3).kind is KeyKind.CTRL_C


def test_translate_resize_returns_resize():
    assert translate(curses.KEY_RESIZE).kind is KeyKind.RESIZE


def test_translate_no_input_returns_unknown():
    assert translate(-1).kind is KeyKind.UNKNOWN


def test_translate_arbitrary_other_returns_unknown():
    assert translate(99999).kind is KeyKind.UNKNOWN
