"""Tests for slugtype.words — pure word-list loading and sampling."""
import random

import pytest

from slugtype import words


def test_load_english_200_returns_200_lowercase_words():
    result = words.load("english-200")
    assert isinstance(result, tuple)
    assert len(result) == 200
    for w in result:
        assert w == w.lower()
        assert w.isalpha()
        assert " " not in w


def test_load_unknown_name_raises():
    with pytest.raises(FileNotFoundError):
        words.load("nonexistent-list")
