"""Render layer tests using a window-shaped recorder fake. No TTY required."""
from dataclasses import replace

from slugtype import render
from slugtype.state import initial_state
from slugtype.stats import Summary
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


def _finished_state_for_render(samples=()):
    s = initial_state(("the",), "time", 60.0)
    s = replace(s, started_at=0.0, ended_at=60.0, finished=True, raw_per_second=tuple(samples))
    return s


def _summary_for_render(wpm=80, acc=95.0):
    return Summary(
        wpm=float(wpm), raw_wpm=float(wpm + 5), accuracy=acc, consistency=72.0,
        correct_chars=400, incorrect_chars=20, extra_chars=5,
    )


def test_result_screen_includes_chart_when_terminal_tall_enough():
    samples = [40 + i for i in range(60)]
    state = _finished_state_for_render(samples=samples)
    summary = _summary_for_render()
    win = WindowRecorder(rows=24, cols=80)

    render.draw_result_screen(win, state, summary, "60s · english-1k", THEME)

    rendered = "\n".join(win.lines().values())
    assert "┤" in rendered or "┼" in rendered
    # At least one plot-line glyph must be drawn in fg_correct (proves the
    # plot body was emitted, not just the axis).
    assert any(
        ch in "─╭╮╯╰│"
        for _, _, text, attr in win.calls
        for ch in text
        if attr == THEME.fg_correct
    )


def test_result_screen_shows_correct_elapsed_time():
    state = _finished_state_for_render(samples=[50.0] * 60)
    summary = _summary_for_render()
    win = WindowRecorder(rows=24, cols=80)

    render.draw_result_screen(win, state, summary, "60s · english-1k", THEME)

    rendered = "\n".join(win.lines().values())
    # Fixture has started_at=0.0, ended_at=60.0 → 60.0s elapsed → "1m00s"
    assert "1m00s" in rendered


def test_result_screen_with_pb_shows_badge():
    state = _finished_state_for_render(samples=[50.0] * 60)
    summary = _summary_for_render(wpm=87)
    win = WindowRecorder(rows=24, cols=80)

    render.draw_result_screen(win, state, summary, "60s · english-1k", THEME, was_pb=True)

    rendered = "\n".join(win.lines().values())
    assert " pb" in rendered or "pb" in rendered.split("87", 1)[1][:20]


def test_result_screen_without_pb_omits_badge():
    state = _finished_state_for_render(samples=[50.0] * 60)
    summary = _summary_for_render(wpm=87)
    win = WindowRecorder(rows=24, cols=80)

    render.draw_result_screen(win, state, summary, "60s · english-1k", THEME, was_pb=False)

    rendered = "\n".join(win.lines().values())
    assert "pb" not in rendered


def test_result_screen_small_terminal_omits_chart():
    state = _finished_state_for_render(samples=[50.0] * 60)
    summary = _summary_for_render()
    win = WindowRecorder(rows=16, cols=80)

    render.draw_result_screen(win, state, summary, "60s · english-1k", THEME)

    rendered = "\n".join(win.lines().values())
    # No chart glyphs at all when rows < 17.
    for ch in "┤┼╭╮╯╰":
        assert ch not in rendered


def test_word_stream_does_not_split_word_mid_character():
    """When a word would overflow the right edge, the WHOLE word wraps to the
    next line — characters are never broken across lines.
    """
    # cols=24, inner_cols=20. Five 4-letter words: "abcd efgh ijkl mnop qrst".
    # "abcd efgh ijkl mnop" = 19 chars, room for 1 more char before inner_cols=20.
    # "qrst " = 5 chars: would push line to 24 — wraps to next line as a whole.
    s = initial_state(("abcd", "efgh", "ijkl", "mnop", "qrst"), "time", 60.0)
    win = WindowRecorder(rows=24, cols=24)
    render.draw_word_stream(win, s, THEME)
    rendered = win.lines()
    # Row 2 is the first wrapped line; row 3 is the second.
    assert "qrst" in rendered.get(3, "")
    assert "qrst" not in rendered.get(2, "")
    # Confirm the previous word is intact on row 2 (no orphaned chars on row 3).
    assert "mnop" in rendered.get(2, "")


def test_word_stream_does_not_split_partially_typed_word_at_edge():
    """The actual bug case: a partially-typed current word at the right edge.

    With OLD per-segment wrap, this would split mid-character because each
    typed char of the current word is its own segment. Concretely:

    cols=28, inner_cols=24.
    Prior submitted words: "abcd " "efgh " "ijkl " "mnop " = 20 chars.
    Current word "qrstuv" with "q" typed produces segments:
      ("q", correct)=1, ("r", caret)=1, ("stuv", dim)=4, (" ", dim)=1 → 7 chars total.
    Block wrap: 20+7=27 > 24, so whole block wraps to line 1 — "qrstuv" intact on row 3.
    Old segment wrap: after col 20, "q" fits (21≤24), "r" fits (22≤24),
      "stuv" at 22+4=26 > 24 → wraps, splitting "qrstuv" across two lines.
    """
    from slugtype.state import TypedChar, WordEntry

    s = initial_state(("abcd", "efgh", "ijkl", "mnop", "qrstuv"), "time", 60.0)
    submitted_words = tuple(
        WordEntry(w, tuple(TypedChar(c, c, "correct") for c in w), submitted=True)
        for w in ("abcd", "efgh", "ijkl", "mnop")
    )
    # "qrstuv" with "q" typed — each typed char is its own segment under _build_word_blocks.
    current_word = WordEntry(
        "qrstuv",
        typed=(TypedChar("q", "q", "correct"),),
        submitted=False,
    )
    s = replace(
        s,
        words=submitted_words + (current_word,),
        current_index=4,
        started_at=0.0,
    )
    win = WindowRecorder(rows=24, cols=28)  # inner_cols=24
    render.draw_word_stream(win, s, THEME)
    rendered = win.lines()

    # "qrstuv" must appear intact on exactly one row.
    rows_with_full_word = [y for y, line in rendered.items() if "qrstuv" in line]
    # Any two-char substring of "qrstuv" on a row that lacks the full word is a split fragment.
    substrings = ("qr", "rs", "st", "tu", "uv")
    rows_with_fragment = [
        y for y, line in rendered.items()
        if any(sub in line for sub in substrings) and "qrstuv" not in line
    ]
    assert len(rows_with_full_word) == 1, (
        f"Expected 'qrstuv' intact on exactly one row; got rows {rows_with_full_word}, "
        f"fragments on {rows_with_fragment}, rendered: {rendered}"
    )
    assert not rows_with_fragment, (
        f"Found word fragments on row(s) {rows_with_fragment}; rendered: {rendered}"
    )
    # Belt-and-suspenders: the prior word "mnop" is on row 2, current word on row 3.
    assert "mnop" in rendered.get(2, ""), f"Expected 'mnop' on row 2; rendered: {rendered}"
    assert "qrstuv" in rendered.get(3, ""), f"Expected 'qrstuv' on row 3; rendered: {rendered}"


def test_word_stream_long_block_falls_back_to_per_segment_wrap():
    """A single block longer than inner_cols (200-char extras-spam) should not
    crash — it falls back to per-segment wrapping and writes what it can.
    """
    s = initial_state(("x" * 200,), "time", 60.0)
    win = WindowRecorder(rows=24, cols=80)
    render.draw_word_stream(win, s, THEME)
    # Should produce calls without raising; exact layout is not asserted.
    assert len(win.calls) > 0
