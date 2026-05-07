"""Tests for slugtype.paths — platform-aware data directory resolution."""
import os
import sys

import pytest

from slugtype import paths


def test_data_dir_macos(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr(paths.Path, "home", classmethod(lambda cls: tmp_path))
    p = paths.data_dir()
    assert str(p).endswith("Library/Application Support/slugtype")
    assert p.is_dir()


def test_data_dir_linux_with_xdg(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    p = paths.data_dir()
    assert p == tmp_path / "slugtype"
    assert p.is_dir()


def test_data_dir_linux_fallback(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)
    monkeypatch.setattr(paths.Path, "home", classmethod(lambda cls: tmp_path))
    p = paths.data_dir()
    assert p == tmp_path / ".local" / "share" / "slugtype"
    assert p.is_dir()


def test_history_path_lives_under_data_dir(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    h = paths.history_path()
    assert h == tmp_path / "slugtype" / "history.jsonl"
