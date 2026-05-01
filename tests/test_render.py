"""Render layer tests using a window-shaped recorder fake. No TTY required."""
from dataclasses import replace

from slugtype import render
from slugtype.state import initial_state
from slugtype.theme import Theme


class WindowRecorder:
    """Record addstr calls so tests can assert on layout without a real curses window."""

    def __init__(self, rows: int = 24, cols: int = 80):
        self.rows = rows
        self.cols = cols
        self.calls: list[tuple[int, int, str, int]] = []

    def getmaxyx(self):
        return (self.rows, self.cols)

    def addstr(self, y, x, text, attr=0):
        self.calls.append((y, x, text, attr))

    def erase(self):
        self.calls.clear()

    def refresh(self):
        pass

    def lines(self) -> dict[int, str]:
        """Reconstruct an approximate per-row string view from the recorded calls."""
        out: dict[int, list[str]] = {}
        for y, x, text, _ in self.calls:
            row = out.setdefault(y, [" "] * self.cols)
            for i, ch in enumerate(text):
                if 0 <= x + i < self.cols:
                    row[x + i] = ch
        return {y: "".join(row).rstrip() for y, row in out.items()}


THEME = Theme(fg_correct=1, fg_dim=2, fg_caret=3, fg_error=4)


def test_bottom_bar_idle_shows_press_any_key_hint():
    s = initial_state(("the",), "time", 60.0)
    win = WindowRecorder(rows=24, cols=80)
    render.draw_bottom_bar(win, s, THEME, now=0.0, live_wpm_value=None)
    line = win.lines()[22]
    assert "1:00" in line
    assert "press any key to start" in line


def test_bottom_bar_running_with_live_wpm():
    s = initial_state(("the",), "time", 60.0)
    s = replace(s, started_at=0.0)
    win = WindowRecorder(rows=24, cols=80)
    render.draw_bottom_bar(win, s, THEME, now=10.0, live_wpm_value=42.0)
    line = win.lines()[22]
    assert "0:50" in line
    assert "42 wpm" in line


def test_bottom_bar_running_without_live_wpm_when_disabled():
    s = initial_state(("the",), "time", 60.0)
    s = replace(s, started_at=0.0)
    win = WindowRecorder(rows=24, cols=80)
    render.draw_bottom_bar(win, s, THEME, now=10.0, live_wpm_value=None)
    line = win.lines()[22]
    assert "0:50" in line
    assert "wpm" not in line


def test_menu_renders_all_items_and_highlights_selected():
    items = [("mode", "time"), ("duration", "60s"), ("language", "english-1k"), ("live wpm", "on")]
    win = WindowRecorder(rows=24, cols=80)
    render.draw_menu(win, items, selected_index=1, theme=THEME)
    rendered = "\n".join(win.lines().values())
    for label, value in items:
        assert label in rendered
        assert value in rendered
    assert any(attr & THEME.fg_caret for _, _, _, attr in win.calls)
