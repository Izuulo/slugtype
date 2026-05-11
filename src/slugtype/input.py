"""Curses keycode → Key enum translation."""
from __future__ import annotations

import curses
from dataclasses import dataclass
from enum import Enum, auto


class KeyKind(Enum):
    CHAR = auto()
    SPACE = auto()
    BACKSPACE = auto()
    TAB = auto()
    ESC = auto()
    ENTER = auto()
    UP = auto()
    DOWN = auto()
    LEFT = auto()
    RIGHT = auto()
    CTRL_C = auto()
    CTRL_R = auto()
    RESIZE = auto()
    UNKNOWN = auto()


@dataclass(frozen=True)
class Key:
    kind: KeyKind
    char: str = ""  # populated only when kind is CHAR


def translate(keycode: int) -> Key:
    if keycode == -1:
        return Key(kind=KeyKind.UNKNOWN)
    if keycode == 3:
        return Key(kind=KeyKind.CTRL_C)
    if keycode == 18:
        return Key(kind=KeyKind.CTRL_R)
    if keycode == 9:
        return Key(kind=KeyKind.TAB)
    if keycode == 27:
        return Key(kind=KeyKind.ESC)
    if keycode in (10, 13, curses.KEY_ENTER):
        return Key(kind=KeyKind.ENTER)
    if keycode == curses.KEY_UP:
        return Key(kind=KeyKind.UP)
    if keycode == curses.KEY_DOWN:
        return Key(kind=KeyKind.DOWN)
    if keycode == curses.KEY_LEFT:
        return Key(kind=KeyKind.LEFT)
    if keycode == curses.KEY_RIGHT:
        return Key(kind=KeyKind.RIGHT)
    if keycode == curses.KEY_RESIZE:
        return Key(kind=KeyKind.RESIZE)
    if keycode in (curses.KEY_BACKSPACE, 127, 8):
        return Key(kind=KeyKind.BACKSPACE)
    if keycode == ord(" "):
        return Key(kind=KeyKind.SPACE)
    # Only accept ASCII range for regular characters
    if 0 <= keycode < 128:
        try:
            ch = chr(keycode)
        except ValueError:
            return Key(kind=KeyKind.UNKNOWN)
        if ch.isprintable() and len(ch) == 1 and not ch.isspace():
            return Key(kind=KeyKind.CHAR, char=ch)
    return Key(kind=KeyKind.UNKNOWN)
