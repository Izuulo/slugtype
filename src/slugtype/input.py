"""Curses keycode → Key enum translation."""
from __future__ import annotations

import curses
from dataclasses import dataclass
from enum import Enum, auto


class KeyKind(Enum):
    CHAR = auto()
    SPACE = auto()
    BACKSPACE = auto()
    CTRL_C = auto()
    RESIZE = auto()
    UNKNOWN = auto()


@dataclass(frozen=True)
class Key:
    kind: KeyKind
    char: str = ""  # populated only when kind is CHAR


def translate(keycode: int) -> Key:
    if keycode == -1:
        return Key(kind=KeyKind.UNKNOWN)
    if keycode == 3:  # Ctrl-C
        return Key(kind=KeyKind.CTRL_C)
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
