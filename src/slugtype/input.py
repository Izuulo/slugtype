"""Curses keycode → Key enum translation."""
from __future__ import annotations

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
