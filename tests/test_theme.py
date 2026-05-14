"""Tests for slugtype.theme — init_pairs tier routing."""
from unittest.mock import MagicMock

import pytest

from slugtype import theme


@pytest.fixture
def fake_curses(monkeypatch):
    """Replace curses calls used by init_pairs with a recording mock.

    Returns the mock so tests can inspect which init_* helpers ran.
    """
    fake = MagicMock()
    fake.color_pair.return_value = 1  # any non-zero int
    monkeypatch.setattr(theme, "curses", fake)
    return fake


def test_init_pairs_routes_to_truecolor_when_can_change_color(fake_curses, monkeypatch):
    fake_curses.can_change_color.return_value = True
    fake_curses.COLORS = 256
    called = []
    monkeypatch.setattr(theme, "_init_truecolor_pairs", lambda: called.append("truecolor"))
    monkeypatch.setattr(theme, "_init_16color_pairs", lambda: called.append("16"))
    monkeypatch.setattr(theme, "_init_8color_pairs", lambda: called.append("8"))

    theme.init_pairs()

    assert called == ["truecolor"]


def test_init_pairs_routes_to_16color_when_cannot_change_but_16_available(fake_curses, monkeypatch):
    fake_curses.can_change_color.return_value = False
    fake_curses.COLORS = 16
    called = []
    monkeypatch.setattr(theme, "_init_truecolor_pairs", lambda: called.append("truecolor"))
    monkeypatch.setattr(theme, "_init_16color_pairs", lambda: called.append("16"))
    monkeypatch.setattr(theme, "_init_8color_pairs", lambda: called.append("8"))

    theme.init_pairs()

    assert called == ["16"]


def test_init_pairs_routes_to_8color_when_only_8_available(fake_curses, monkeypatch):
    fake_curses.can_change_color.return_value = True
    fake_curses.COLORS = 8
    called = []
    monkeypatch.setattr(theme, "_init_truecolor_pairs", lambda: called.append("truecolor"))
    monkeypatch.setattr(theme, "_init_16color_pairs", lambda: called.append("16"))
    monkeypatch.setattr(theme, "_init_8color_pairs", lambda: called.append("8"))

    theme.init_pairs()

    assert called == ["8"]


def test_init_pairs_returns_theme_with_four_pair_indices(fake_curses, monkeypatch):
    fake_curses.can_change_color.return_value = True
    fake_curses.COLORS = 256
    monkeypatch.setattr(theme, "_init_truecolor_pairs", lambda: None)

    result = theme.init_pairs()

    assert result.fg_correct == 1
    assert result.fg_dim == 1
    assert result.fg_caret == 1
    assert result.fg_error == 1
    # color_pair was called for each of the four PAIR_ constants
    assert fake_curses.color_pair.call_count == 4
