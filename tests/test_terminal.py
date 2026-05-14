"""Tests for slugtype.terminal — session lifecycle and escape-delay configuration."""
import os

from slugtype.terminal import MIN_COLS, MIN_ROWS, _configure_escape_delay, is_too_small


def test_configure_escape_delay_sets_env_var_to_25(monkeypatch):
    monkeypatch.delenv("ESCDELAY", raising=False)
    _configure_escape_delay()
    assert os.environ["ESCDELAY"] == "25"


def test_configure_escape_delay_respects_existing_value(monkeypatch):
    monkeypatch.setenv("ESCDELAY", "100")
    _configure_escape_delay()
    assert os.environ["ESCDELAY"] == "100"


def test_is_too_small_below_min_cols():
    assert is_too_small(rows=MIN_ROWS, cols=MIN_COLS - 1) is True


def test_is_too_small_below_min_rows():
    assert is_too_small(rows=MIN_ROWS - 1, cols=MIN_COLS) is True


def test_is_too_small_at_minimum_boundary_is_false():
    assert is_too_small(rows=MIN_ROWS, cols=MIN_COLS) is False


def test_is_too_small_above_minimum_is_false():
    assert is_too_small(rows=40, cols=120) is False
