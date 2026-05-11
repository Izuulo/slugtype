"""Tests for slugtype.terminal — session lifecycle and escape-delay configuration."""
import os

from slugtype.terminal import _configure_escape_delay


def test_configure_escape_delay_sets_env_var_to_25(monkeypatch):
    monkeypatch.delenv("ESCDELAY", raising=False)
    _configure_escape_delay()
    assert os.environ["ESCDELAY"] == "25"


def test_configure_escape_delay_respects_existing_value(monkeypatch):
    monkeypatch.setenv("ESCDELAY", "100")
    _configure_escape_delay()
    assert os.environ["ESCDELAY"] == "100"
