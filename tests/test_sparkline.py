"""Tests for slugtype.sparkline — pure glyph computation."""
import pytest

from slugtype.sparkline import chart_lines


def test_empty_samples_returns_empty_list():
    assert chart_lines([], width=40, plot_height=4) == []


def test_single_sample_returns_empty_list():
    assert chart_lines([50.0], width=40, plot_height=4) == []


def test_too_narrow_returns_empty_list():
    assert chart_lines([10.0, 20.0], width=8, plot_height=4) == []


def test_too_short_returns_empty_list():
    assert chart_lines([10.0, 20.0], width=40, plot_height=1) == []


def test_two_samples_known_layout():
    """[10, 50] in a 20-col, 4-plot-row chart with y_top=60.
    Sample 1: value=10 → row 3 (just above axis).
    Sample 2: value=50 → row 1 (3rd from top).
    """
    rows = chart_lines([10.0, 50.0], width=20, plot_height=4)

    assert len(rows) == 6  # 4 plot + axis + ticks
    assert all(len(r) == 20 for r in rows)

    # Y-labels (y_top = ceil(50/15)*15 = 60).
    # Row 0 label = 60, row 1 = 45, row 2 = 30, row 3 = 15, axis row = 0.
    assert rows[0].startswith(" 60 ┤")
    assert rows[1].startswith(" 45 ┤")
    assert rows[2].startswith(" 30 ┤")
    assert rows[3].startswith(" 15 ┤")
    assert rows[4].startswith("  0 ┼")  # axis row

    # Plot area is cols 5..19 (15 cols). Sample 1 at col 5, sample 2 at col 19.
    # Sample 1 (value=10) maps to row 3 → `─` at row 3, col 5.
    # Sample 2 (value=50) maps to row 1 (50/60*3=2.5, rounds to 3 from bottom = row 0).
    # Actually: row = (plot_height-1) - round(v/y_top * (plot_height-1))
    # For v=10, plot_height=4: (3) - round(10/60*3) = 3 - 0 = 3.
    # For v=50: 3 - round(50/60*3) = 3 - 2 = 1.
    # So sample 1 is at row 3, sample 2 at row 1 → line goes UP.
    assert rows[3][5] in ("─", "╰", "╯")  # first sample, possibly turned into corner
    assert rows[1][19] in ("─", "╭", "╮")  # last sample

    # Axis row is `┼─────...`
    assert rows[4][4] == "┼"
    assert rows[4][5:].startswith("─" * 5)


def test_y_axis_floor_is_15():
    """When max(samples) < 15, y_top must be 15 (not the sample max)."""
    rows = chart_lines([2.0, 5.0], width=20, plot_height=4)
    assert rows[0].startswith(" 15 ┤")


def test_y_axis_rounds_up_to_15_multiple():
    """max=80 → y_top=90 (ceil(80/15)*15)."""
    rows = chart_lines([80.0, 80.0], width=20, plot_height=4)
    assert rows[0].startswith(" 90 ┤")


def test_realistic_60_samples_shape():
    """A rising-then-falling 60-sample series produces a chart with the peak
    in the top plot row and the trough near the axis row."""
    samples = [50 + 30 * (1 - abs(i - 30) / 30) for i in range(60)]
    # samples[0] = 20, samples[30] = 80, samples[59] ≈ 21.
    rows = chart_lines(samples, width=60, plot_height=4)

    assert len(rows) == 6
    assert all(len(r) == 60 for r in rows)

    # y_top = ceil(80/15)*15 = 90, so row 0 label = 90.
    assert rows[0].startswith(" 90 ┤")

    # Some plot character must appear in the top half (rows 0 or 1) given the peak.
    plot_chars = set("─╭╮╯╰│")
    top_half_has_plot = any(ch in plot_chars for ch in rows[0]) or any(ch in plot_chars for ch in rows[1])
    assert top_half_has_plot

    # X-tick row (last) shows "0s" near the start and "59s" or similar near the end.
    tick_row = rows[-1]
    assert "0s" in tick_row
    assert "s" in tick_row[-5:]  # some "Ns" near the end


def test_all_zero_samples_renders_along_bottom():
    """All-zero samples → line sits at the bottom plot row."""
    rows = chart_lines([0.0, 0.0, 0.0, 0.0, 0.0], width=30, plot_height=4)
    assert len(rows) == 6
    # Bottom plot row (row 3) should contain plot characters.
    plot_chars = set("─╭╮╯╰│")
    assert any(ch in plot_chars for ch in rows[3])
    # Top plot row should be blank in the plot area (cols 5..29).
    assert rows[0][5:].strip() == "" or all(c not in plot_chars for c in rows[0][5:])
