"""Word-list loading and sampling. Pure given a seeded RNG."""
from __future__ import annotations

import random
from importlib.resources import files


def load(name: str) -> tuple[str, ...]:
    """Load a word list from the bundled data/ directory.

    Returns a tuple of words. Raises FileNotFoundError if the named list
    does not exist.
    """
    data_file = files("slugtype.data").joinpath(f"{name}.txt")
    text = data_file.read_text(encoding="utf-8")
    word_list = tuple(line.strip() for line in text.splitlines() if line.strip())
    if not word_list:
        raise ValueError(f"word list {name!r} is empty")
    return word_list


def sample(word_list: tuple[str, ...], n: int, rng: random.Random) -> tuple[str, ...]:
    """Sample n words from word_list with replacement using the provided RNG.

    n may exceed len(word_list); n=0 returns an empty tuple.
    """
    if n <= 0:
        return ()
    return tuple(rng.choice(word_list) for _ in range(n))
