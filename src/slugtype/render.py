"""Curses rendering. Pure(ish) over a curses window — no global state."""
from __future__ import annotations

import curses

from slugtype.state import TestState
from slugtype.theme import Theme


def draw(window: "curses.window", state: TestState, theme: Theme, config_label: str, now: float) -> None:
    window.erase()
    draw_top_bar(window, config_label, theme)
    draw_word_stream(window, state, theme)
    draw_bottom_bar(window, state, theme, now)
    window.refresh()


def draw_top_bar(window: "curses.window", config_label: str, theme: Theme) -> None:
    rows, cols = window.getmaxyx()
    left = "slugtype"
    right = config_label
    pad = max(1, cols - len(left) - len(right) - 2)
    text = f" {left}{' ' * pad}{right} "
    text = text[:cols]
    window.addstr(0, 0, text, theme.fg_dim)


def draw_word_stream(window: "curses.window", state: TestState, theme: Theme) -> None:
    """Render the current word and the next two lines of upcoming words.

    The current word is highlighted character by character based on the
    user's typed buffer; upcoming words render dim; the caret is drawn at
    the typing cursor inside the current word.
    """
    rows, cols = window.getmaxyx()
    inner_cols = cols - 4  # 2-col left/right margin
    if inner_cols < 10:
        return  # too narrow to render anything meaningful

    # Build a flat list of (text, attr, is_caret_target) segments for the current word and all upcoming words.
    segments: list[tuple[str, int, bool]] = []

    for idx, word in enumerate(state.words):
        if word.submitted and idx < state.current_index:
            continue  # already-completed words scroll out of view
        if idx == state.current_index:
            # Render typed chars with their categorical color.
            for tc in word.typed:
                if tc.category == "correct":
                    segments.append((tc.typed, theme.fg_correct, False))
                elif tc.category == "incorrect":
                    segments.append((tc.expected or tc.typed, theme.fg_error, False))
                else:  # extra
                    segments.append((tc.typed, theme.fg_error | curses.A_DIM, False))
            # Caret marker (one segment so we know where to flash a block).
            untyped_start = len(word.typed)
            untyped_correct = word.expected[untyped_start:]
            if untyped_correct:
                # First untyped char gets the caret highlight; rest is dim foreground.
                segments.append((untyped_correct[0], theme.fg_caret | curses.A_REVERSE, True))
                if len(untyped_correct) > 1:
                    segments.append((untyped_correct[1:], theme.fg_correct | curses.A_DIM, False))
            segments.append((" ", theme.fg_dim, False))
        else:
            segments.append((word.expected, theme.fg_dim, False))
            segments.append((" ", theme.fg_dim, False))

    # Layout segments into 3 lines of `inner_cols` width, breaking on spaces.
    lines: list[list[tuple[str, int]]] = [[]]
    line_lens = [0]
    for text, attr, _ in segments:
        # If adding this segment overflows, soft-wrap on the boundary.
        if line_lens[-1] + len(text) > inner_cols and len(lines) < 3:
            lines.append([])
            line_lens.append(0)
            if text == " ":
                continue  # don't start a new line with a space
        if len(lines) > 3:
            break
        lines[-1].append((text, attr))
        line_lens[-1] += len(text)

    # Draw three lines starting at row 2.
    for i, segs in enumerate(lines[:3]):
        x = 2
        y = 2 + i
        for text, attr in segs:
            try:
                window.addstr(y, x, text, attr)
            except curses.error:
                pass  # writing to bottom-right corner can fail; ignore
            x += len(text)


def draw_bottom_bar(window: "curses.window", state: TestState, theme: Theme, now: float) -> None:
    rows, cols = window.getmaxyx()
    y = rows - 2

    if state.started_at is None:
        left = format_progress(state, elapsed=0.0)
        center = "press any key to start"
    else:
        end = state.ended_at if state.ended_at is not None else now
        elapsed = end - state.started_at
        left = format_progress(state, elapsed=elapsed)
        center = ""

    pad_right = max(0, cols - len(left) - len(center) - 4)
    text = f" {left}  {center}{' ' * pad_right} "
    text = text[:cols]
    window.addstr(y, 0, text, theme.fg_dim)


def format_progress(state: TestState, elapsed: float) -> str:
    if state.mode == "time":
        remaining = max(0.0, state.duration_s - elapsed)
        m = int(remaining // 60)
        s = int(remaining % 60)
        return f"{m}:{s:02d}"
    # words mode: how many words submitted so far
    submitted = sum(1 for w in state.words if w.submitted)
    return f"{submitted}/{len(state.words)}"
