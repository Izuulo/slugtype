"""Curses session lifecycle: alt-screen, raw mode, restore on exit."""
from __future__ import annotations

import curses
import os
import sys
from contextlib import contextmanager
from typing import Iterator


MIN_COLS = 60
MIN_ROWS = 15


class TerminalTooSmallError(RuntimeError):
    pass


def _configure_escape_delay() -> None:
    """Make Esc responsive. Default ESCDELAY is 1000ms with many curses builds,
    which makes single Esc presses lag and causes arrow-key escape sequences
    to deliver bare ESC when the buffer drains too quickly. 25ms is enough for
    ncurses to coalesce arrow-key sequences without blocking real Esc presses.
    Must be called before curses.initscr() — ncurses reads ESCDELAY at init.
    """
    os.environ.setdefault("ESCDELAY", "25")


def is_too_small(rows: int, cols: int,
                 min_cols: int = MIN_COLS,
                 min_rows: int = MIN_ROWS) -> bool:
    """True if the terminal is below the minimum slugtype needs.

    The minimum boundary is inclusive: is_too_small(MIN_ROWS, MIN_COLS) is False.
    """
    return cols < min_cols or rows < min_rows


@contextmanager
def session() -> Iterator["curses.window"]:
    """Enter alt-screen + raw mode for the duration of the block.

    Raises TerminalTooSmallError if the terminal is below MIN_COLS x MIN_ROWS
    when entering. On exit (normal or exceptional) restores the terminal.
    """
    _configure_escape_delay()
    stdscr = curses.initscr()
    try:
        curses.noecho()
        curses.cbreak()
        curses.raw()
        stdscr.keypad(True)
        try:
            curses.curs_set(0)
        except curses.error:
            pass  # cursor visibility not supported

        rows, cols = stdscr.getmaxyx()
        if cols < MIN_COLS or rows < MIN_ROWS:
            raise TerminalTooSmallError(
                f"slugtype: needs at least {MIN_COLS}x{MIN_ROWS}, got {cols}x{rows}"
            )

        yield stdscr
    finally:
        try:
            curses.curs_set(1)
        except curses.error:
            pass
        stdscr.keypad(False)
        curses.noraw()
        curses.nocbreak()
        curses.echo()
        curses.endwin()
