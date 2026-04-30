"""Curses session lifecycle: alt-screen, raw mode, restore on exit."""
from __future__ import annotations

import curses
import sys
from contextlib import contextmanager
from typing import Iterator


MIN_COLS = 60
MIN_ROWS = 15


class TerminalTooSmallError(RuntimeError):
    pass


@contextmanager
def session() -> Iterator["curses.window"]:
    """Enter alt-screen + raw mode for the duration of the block.

    Raises TerminalTooSmallError if the terminal is below MIN_COLS x MIN_ROWS
    when entering. On exit (normal or exceptional) restores the terminal.
    """
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
