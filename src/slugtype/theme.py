"""Color palette resolution. v0.1 ships a single serika-dark theme."""
from __future__ import annotations

import curses
from dataclasses import dataclass


# Curses color-pair indices used across the app. These are stable identifiers;
# the actual RGB they map to is set up by `init_pairs` once curses has started.
PAIR_FG_CORRECT = 1
PAIR_FG_DIM = 2
PAIR_FG_CARET = 3
PAIR_FG_ERROR = 4


@dataclass(frozen=True)
class Theme:
    fg_correct: int
    fg_dim: int
    fg_caret: int
    fg_error: int


def init_pairs() -> Theme:
    """Initialize curses color pairs and return the Theme that references them.

    Must be called after curses.start_color(). Assumes the terminal supports
    24-bit color or a reasonable approximation; full 256/16-color fallback
    lands at v1.0.
    """
    curses.start_color()
    curses.use_default_colors()  # let the terminal background show through

    # Define foreground colors. If the terminal can change colors, set RGB
    # values approximating Monkeytype's serika-dark palette. Otherwise rely
    # on default basic colors.
    if curses.can_change_color():
        # init_color uses 0..1000 scale
        curses.init_color(10, 819, 816, 773)   # fg_correct  #d1d0c5
        curses.init_color(11, 392, 400, 411)   # fg_dim      #646669
        curses.init_color(12, 886, 718, 79)    # fg_caret    #e2b714
        curses.init_color(13, 792, 278, 329)   # fg_error    #ca4754
        curses.init_pair(PAIR_FG_CORRECT, 10, -1)
        curses.init_pair(PAIR_FG_DIM, 11, -1)
        curses.init_pair(PAIR_FG_CARET, 12, -1)
        curses.init_pair(PAIR_FG_ERROR, 13, -1)
    else:
        # Best effort with built-in 8 colors.
        curses.init_pair(PAIR_FG_CORRECT, curses.COLOR_WHITE, -1)
        curses.init_pair(PAIR_FG_DIM, curses.COLOR_BLACK, -1)
        curses.init_pair(PAIR_FG_CARET, curses.COLOR_YELLOW, -1)
        curses.init_pair(PAIR_FG_ERROR, curses.COLOR_RED, -1)

    return Theme(
        fg_correct=curses.color_pair(PAIR_FG_CORRECT),
        fg_dim=curses.color_pair(PAIR_FG_DIM),
        fg_caret=curses.color_pair(PAIR_FG_CARET),
        fg_error=curses.color_pair(PAIR_FG_ERROR),
    )
