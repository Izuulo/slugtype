"""Curses rendering. Pure(ish) over a curses window — no global state."""
from __future__ import annotations

import curses

from slugtype import sparkline
from slugtype.state import TestState
from slugtype.theme import Theme


def draw(window: "curses.window", state: TestState, theme: Theme, config_label: str, now: float, live_wpm_value: float | None = None) -> None:
    window.erase()
    draw_top_bar(window, config_label, theme)
    draw_word_stream(window, state, theme)
    draw_bottom_bar(window, state, theme, now, live_wpm_value)
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
    """Render the test as a flowing paragraph: submitted words stay visible
    in their final colors, the current word carries the caret, upcoming words
    render dim. The visible 3-line viewport scrolls to keep the caret in view.
    """
    rows, cols = window.getmaxyx()
    inner_cols = cols - 4  # 2-col left/right margin
    if inner_cols < 10:
        return

    segments, caret_seg_idx = _build_segments(state, theme)
    lines, caret_line = _layout_lines(segments, caret_seg_idx, inner_cols)

    # Viewport: 3 lines with the caret on line 0 (first row) until enough
    # text has been typed to scroll, after which the caret stays on line 1.
    viewport_top = max(0, caret_line - 1)
    max_top = max(0, len(lines) - 3)
    viewport_top = min(viewport_top, max_top)

    for i, line in enumerate(lines[viewport_top : viewport_top + 3]):
        x = 2
        y = 2 + i
        for text, attr in line:
            try:
                window.addstr(y, x, text, attr)
            except curses.error:
                pass
            x += len(text)


def _build_segments(state: TestState, theme: Theme) -> tuple[list[tuple[str, int]], int]:
    """Build a flat list of (text, attr) segments covering every word in the
    test. Returns (segments, caret_segment_index).
    """
    segments: list[tuple[str, int]] = []
    caret_idx = -1

    for idx, word in enumerate(state.words):
        is_current = idx == state.current_index and not word.submitted

        if is_current:
            # Typed chars in their categorical colors.
            for tc in word.typed:
                if tc.category == "correct":
                    segments.append((tc.typed, theme.fg_correct))
                elif tc.category == "incorrect":
                    segments.append((tc.expected or tc.typed, theme.fg_error))
                else:  # extra
                    segments.append((tc.typed, theme.fg_error | curses.A_DIM))
            # Caret + remaining expected chars.
            untyped = word.expected[len(word.typed):]
            if untyped:
                caret_idx = len(segments)
                segments.append((untyped[0], theme.fg_caret | curses.A_REVERSE))
                if len(untyped) > 1:
                    segments.append((untyped[1:], theme.fg_correct | curses.A_DIM))
                segments.append((" ", theme.fg_dim))
            else:
                # Cursor is past the expected length (all typed, possibly extras);
                # park the caret on the trailing space.
                caret_idx = len(segments)
                segments.append((" ", theme.fg_caret | curses.A_REVERSE))
        elif word.submitted:
            # Already-typed word: show what was typed in its final colors.
            for tc in word.typed:
                if tc.category == "correct":
                    segments.append((tc.typed, theme.fg_correct))
                elif tc.category == "incorrect":
                    segments.append((tc.expected or tc.typed, theme.fg_error))
                else:  # extra
                    segments.append((tc.typed, theme.fg_error | curses.A_DIM))
            # Any expected chars never typed get rendered dim ("missed").
            missed = word.expected[len(word.typed):]
            if missed:
                segments.append((missed, theme.fg_dim))
            segments.append((" ", theme.fg_dim))
        else:
            # Upcoming word.
            segments.append((word.expected, theme.fg_dim))
            segments.append((" ", theme.fg_dim))

    return segments, caret_idx


def _layout_lines(
    segments: list[tuple[str, int]],
    caret_seg_idx: int,
    inner_cols: int,
) -> tuple[list[list[tuple[str, int]]], int]:
    """Soft-wrap segments into lines of width ≤ inner_cols. Returns
    (lines, caret_line_index).
    """
    lines: list[list[tuple[str, int]]] = [[]]
    line_lens = [0]
    caret_line = 0

    for seg_idx, (text, attr) in enumerate(segments):
        if line_lens[-1] + len(text) > inner_cols:
            lines.append([])
            line_lens.append(0)
            if text == " ":
                # don't start a new line with a space
                if seg_idx == caret_seg_idx:
                    caret_line = len(lines) - 1
                continue
        if seg_idx == caret_seg_idx:
            caret_line = len(lines) - 1
        lines[-1].append((text, attr))
        line_lens[-1] += len(text)

    return lines, caret_line


def draw_bottom_bar(window: "curses.window", state: TestState, theme: Theme, now: float, live_wpm_value: float | None = None) -> None:
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

    right = ""
    if live_wpm_value is not None and state.started_at is not None and not state.finished:
        right = f"{round(live_wpm_value)} wpm"

    pad = max(1, cols - len(left) - len(center) - len(right) - 4)
    text = f" {left}  {center}{' ' * pad}{right} "
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


def draw_result_screen(
    window: "curses.window",
    state: TestState,
    summary,
    config_label: str,
    theme: Theme,
    was_pb: bool = False,
) -> None:
    """End-of-test result screen: wpm / acc / raw / consistency headline,
    plus characters and time below.
    """
    window.erase()
    rows, cols = window.getmaxyx()

    # Top bar
    left = "slugtype — result"
    right = config_label
    pad = max(1, cols - len(left) - len(right) - 2)
    window.addstr(0, 0, f" {left}{' ' * pad}{right} "[:cols], theme.fg_dim)

    # Four-column headline: wpm / acc / raw / consistency
    wpm_value = str(round(summary.wpm))
    if was_pb:
        wpm_value = f"{wpm_value} pb"
    metrics = (
        ("wpm", wpm_value),
        ("acc", f"{summary.accuracy:.1f}%"),
        ("raw", str(round(summary.raw_wpm))),
        ("consistency", f"{summary.consistency:.1f}%"),
    )
    col_width = max(14, cols // (len(metrics) + 1))
    total_width = col_width * len(metrics)
    start_x = max(2, (cols - total_width) // 2)
    headline_y = max(4, rows // 3 - 1)

    for i, (label, value) in enumerate(metrics):
        col_center = start_x + i * col_width + col_width // 2
        try:
            window.addstr(headline_y, col_center - len(label) // 2, label, theme.fg_dim)
            window.addstr(headline_y + 2, col_center - len(value) // 2, value, theme.fg_caret)
        except curses.error:
            pass

    # Chart between headline and sub-stats. Total rows = plot rows + axis row + tick row.
    chart_height = 6
    chart_width = min(60, cols - 4)
    chart_x = max(2, (cols - chart_width) // 2)
    chart_y = headline_y + 4
    drawn = _draw_sparkline(
        window, state.raw_per_second, x=chart_x, y=chart_y,
        width=chart_width, plot_height=chart_height - 2, theme=theme,
    )

    # Sub-row: characters + time. Y depends on whether chart was drawn.
    sub_y = chart_y + drawn + 1 if drawn else headline_y + 6
    elapsed = (state.ended_at - state.started_at) if state.started_at is not None and state.ended_at is not None else 0.0
    sub_metrics = (
        ("characters", f"{summary.correct_chars} / {summary.incorrect_chars} / {summary.extra_chars}"),
        ("time", _format_elapsed(elapsed)),
    )
    sub_col_width = max(20, cols // (len(sub_metrics) + 1))
    sub_total_width = sub_col_width * len(sub_metrics)
    sub_start_x = max(2, (cols - sub_total_width) // 2)
    for i, (label, value) in enumerate(sub_metrics):
        col_center = sub_start_x + i * sub_col_width + sub_col_width // 2
        try:
            window.addstr(sub_y, col_center - len(label) // 2, label, theme.fg_dim)
            window.addstr(sub_y + 1, col_center - len(value) // 2, value, theme.fg_correct)
        except curses.error:
            pass

    # Hint
    hint = "tab restart · esc menu · any other key exits"
    hint_x = max(2, (cols - len(hint)) // 2)
    try:
        window.addstr(rows - 2, hint_x, hint, theme.fg_dim)
    except curses.error:
        pass

    window.refresh()


def _format_elapsed(elapsed_s: float) -> str:
    if elapsed_s >= 60:
        m = int(elapsed_s // 60)
        s = int(round(elapsed_s % 60))
        return f"{m}m{s:02d}s"
    return f"{elapsed_s:.1f}s"


def _draw_sparkline(window: "curses.window", samples, x: int, y: int, width: int, plot_height: int, theme: Theme) -> int:
    """Render a sparkline at (y, x). Returns the number of rows written
    (0 if the chart was omitted because chart_lines returned []).
    """
    rows_text = sparkline.chart_lines(samples, width=width, plot_height=plot_height)
    if not rows_text:
        return 0
    plot_chars = set("─╭╮╯╰│")
    for i, line in enumerate(rows_text):
        # Color the plot characters with fg_correct, axis/labels with fg_dim.
        col = x
        for ch in line:
            attr = theme.fg_correct if ch in plot_chars else theme.fg_dim
            try:
                window.addstr(y + i, col, ch, attr)
            except curses.error:
                pass
            col += 1
    return len(rows_text)


def draw_menu(
    window: "curses.window",
    items: list[tuple[str, str]],
    selected_index: int,
    theme: Theme,
) -> None:
    """Centered modal listing menu items as `label  value` rows.

    `items` is a list of (label, current_value_string) pairs. `selected_index`
    is the row to highlight.
    """
    rows, cols = window.getmaxyx()

    inner_width = max(28, max((len(lbl) + len(val) for lbl, val in items), default=24) + 8)
    box_width = min(cols - 4, inner_width + 4)
    box_height = len(items) + 4
    box_top = max(0, (rows - box_height) // 2)
    box_left = max(0, (cols - box_width) // 2)

    horiz = "─" * (box_width - 2)
    try:
        window.addstr(box_top, box_left, "┌" + horiz + "┐", theme.fg_dim)
        for i in range(1, box_height - 1):
            window.addstr(box_top + i, box_left, "│" + " " * (box_width - 2) + "│", theme.fg_dim)
        window.addstr(box_top + box_height - 1, box_left, "└" + horiz + "┘", theme.fg_dim)
    except curses.error:
        pass

    title = "settings"
    try:
        window.addstr(box_top + 1, box_left + (box_width - len(title)) // 2, title, theme.fg_dim)
    except curses.error:
        pass

    for i, (label, value) in enumerate(items):
        y = box_top + 3 + i
        attr_label = theme.fg_caret if i == selected_index else theme.fg_correct
        attr_value = theme.fg_caret | curses.A_REVERSE if i == selected_index else theme.fg_dim
        try:
            window.addstr(y, box_left + 3, label, attr_label)
            value_x = box_left + box_width - 3 - len(value)
            window.addstr(y, value_x, value, attr_value)
        except curses.error:
            pass

    window.refresh()
