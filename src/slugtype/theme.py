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


def _init_truecolor_pairs() -> None:
    """Tier 1: terminal supports user-defined RGB. Use exact serika colors."""
    curses.init_color(10, 819, 816, 773)   # fg_correct  #d1d0c5
    curses.init_color(11, 392, 400, 411)   # fg_dim      #646669
    curses.init_color(12, 886, 718, 79)    # fg_caret    #e2b714
    curses.init_color(13, 792, 278, 329)   # fg_error    #ca4754
    curses.init_pair(PAIR_FG_CORRECT, 10, -1)
    curses.init_pair(PAIR_FG_DIM, 11, -1)
    curses.init_pair(PAIR_FG_CARET, 12, -1)
    curses.init_pair(PAIR_FG_ERROR, 13, -1)


def _init_16color_pairs() -> None:
    """Tier 2: 16 colors available but can't redefine. Use bright variants:
    index 8 is the canonical 'bright black' = gray on every modern theme,
    visible on both dark and light backgrounds.
    """
    curses.init_pair(PAIR_FG_CORRECT, curses.COLOR_WHITE, -1)
    curses.init_pair(PAIR_FG_DIM, 8, -1)       # bright black / gray
    curses.init_pair(PAIR_FG_CARET, 11, -1)    # bright yellow
    curses.init_pair(PAIR_FG_ERROR, curses.COLOR_RED, -1)


def _init_8color_pairs() -> None:
    """Tier 3: only the basic 8 colors. Accept loss of typed/untyped contrast
    so dim text remains visible. The caret and red errors still distinguish
    position and mistakes.
    """
    curses.init_pair(PAIR_FG_CORRECT, curses.COLOR_WHITE, -1)
    curses.init_pair(PAIR_FG_DIM, curses.COLOR_WHITE, -1)   # same as correct
    curses.init_pair(PAIR_FG_CARET, curses.COLOR_YELLOW, -1)
    curses.init_pair(PAIR_FG_ERROR, curses.COLOR_RED, -1)


def init_pairs() -> Theme:
    """Initialize curses color pairs and return the Theme that references them.

    Must be called after curses.start_color(). Three tiers:
      1. can_change_color() and COLORS >= 16 — exact serika RGB
      2. COLORS >= 16 — bright-variant fallback (visible dim text)
      3. otherwise — readable 8-color fallback (correct/dim collapse)
    """
    curses.start_color()
    curses.use_default_colors()  # let the terminal background show through

    if curses.can_change_color() and curses.COLORS >= 16:
        _init_truecolor_pairs()
    elif curses.COLORS >= 16:
        _init_16color_pairs()
    else:
        _init_8color_pairs()

    return Theme(
        fg_correct=curses.color_pair(PAIR_FG_CORRECT),
        fg_dim=curses.color_pair(PAIR_FG_DIM),
        fg_caret=curses.color_pair(PAIR_FG_CARET),
        fg_error=curses.color_pair(PAIR_FG_ERROR),
    )
