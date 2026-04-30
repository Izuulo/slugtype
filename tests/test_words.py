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


def test_sample_is_deterministic_with_seeded_rng():
    word_list = ("alpha", "beta", "gamma", "delta")
    rng_a = random.Random(42)
    rng_b = random.Random(42)
    assert words.sample(word_list, 10, rng_a) == words.sample(word_list, 10, rng_b)


def test_sample_returns_n_words():
    word_list = ("alpha", "beta", "gamma")
    result = words.sample(word_list, 7, random.Random(0))
    assert len(result) == 7
    for w in result:
        assert w in word_list


def test_sample_with_n_larger_than_list_uses_replacement():
    word_list = ("only-one",)
    result = words.sample(word_list, 5, random.Random(0))
    assert len(result) == 5
    assert all(w == "only-one" for w in result)


def test_sample_returns_empty_when_n_is_zero():
    word_list = ("alpha", "beta")
    assert words.sample(word_list, 0, random.Random(0)) == ()
