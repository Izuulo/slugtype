"""Pure glyph computation for the per-second WPM sparkline. No curses.

The chart is built as a 2D grid of plot characters, then prefixed with
y-axis labels and suffixed with an axis row + x-tick row.
"""
from __future__ import annotations

import math
from typing import Sequence


LABEL_WIDTH = 4  # "NNN " right-aligned label, then "┤" on plot rows / "┼" on axis row


def chart_lines(samples: Sequence[float], width: int, plot_height: int = 4) -> list[str]:
    """Render `samples` as a sparkline.

    Returns `plot_height + 2` strings (plot rows + axis row + x-tick row),
    each exactly `width` chars. Returns [] when the chart cannot be drawn:
    fewer than 2 samples, width < 10, or plot_height < 2.
    """
    if len(samples) < 2 or width < 10 or plot_height < 2:
        return []
    if not all(math.isfinite(s) for s in samples):
        return []

    plot_width = width - LABEL_WIDTH - 1  # -1 for the "┤"/"┼" edge column

    # Y-axis range: 0 to ceil(max/15)*15, with a floor of 15.
    raw_max = max(samples)
    y_top = max(15, int(math.ceil(raw_max / 15) * 15))

    # Map each plot column to a sample index, then to a row (0=top, plot_height-1=bottom).
    n = len(samples)
    col_rows = []
    for c in range(plot_width):
        idx = round(c * (n - 1) / max(1, plot_width - 1))
        v = samples[idx]
        r = (plot_height - 1) - round(v / y_top * (plot_height - 1))
        # Clamp defensively.
        r = max(0, min(plot_height - 1, r))
        col_rows.append(r)

    # Build a 2D grid of plot characters.
    grid = [[" "] * plot_width for _ in range(plot_height)]
    for c in range(plot_width):
        r = col_rows[c]
        if c == 0:
            grid[r][c] = "─"
            continue
        prev_r = col_rows[c - 1]
        if r == prev_r:
            grid[r][c] = "─"
        elif r < prev_r:
            # Going up. Previous col turns up (╯), this col starts the new level (╭).
            if grid[prev_r][c - 1] in (" ", "─", "╰"):
                grid[prev_r][c - 1] = "╯"
            grid[r][c] = "╭"
            for rr in range(r + 1, prev_r):
                if grid[rr][c - 1] == " ":
                    grid[rr][c - 1] = "│"
        else:
            # Going down. Previous col turns down (╮), this col starts new level (╰).
            if grid[prev_r][c - 1] in (" ", "─", "╭"):
                grid[prev_r][c - 1] = "╮"
            grid[r][c] = "╰"
            for rr in range(prev_r + 1, r):
                if grid[rr][c - 1] == " ":
                    grid[rr][c - 1] = "│"

    # Y-axis labels: top row = y_top, evenly stepping down to y_top/plot_height
    # at the bottom plot row. The axis row (separate) shows 0.
    # Divides by plot_height so the spacing matches the y_top/plot_height step size.
    plot_lines: list[str] = []
    for r in range(plot_height):
        label_value = round(y_top * (plot_height - r) / plot_height)
        label = f"{label_value:>3} ┤"
        plot_lines.append(label + "".join(grid[r]))

    axis_line = f"{0:>{LABEL_WIDTH - 1}} ┼" + "─" * plot_width

    # X-tick row: 5 ticks evenly spaced. Sample indices run 0..(n-1).
    tick_chars = [" "] * width
    tick_positions = [0, plot_width // 4, plot_width // 2, 3 * plot_width // 4, plot_width - 1]
    for pos in tick_positions:
        tick_value = round(pos * (n - 1) / max(1, plot_width - 1))
        s = f"{tick_value}s"
        start = LABEL_WIDTH + 1 + pos
        # Right-align labels that would overflow the right edge.
        if start + len(s) > width:
            start = width - len(s)
        for i, ch in enumerate(s):
            target = start + i
            if 0 <= target < width:
                tick_chars[target] = ch
    tick_line = "".join(tick_chars)

    # Pad/truncate every line to exactly `width`.
    out = []
    for line in plot_lines + [axis_line, tick_line]:
        if len(line) < width:
            line = line + " " * (width - len(line))
        elif len(line) > width:
            line = line[:width]
        out.append(line)
    return out
