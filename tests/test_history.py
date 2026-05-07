"""Tests for slugtype.history — JSONL persistence and PB queries."""
import os
from datetime import datetime, timezone

import pytest

from slugtype import history
from slugtype.run import Config
from slugtype.state import TestState, WordEntry, TypedChar
from slugtype.stats import Summary


def _finished_state(duration: float = 60.0, samples=()) -> TestState:
    """Build a minimal finished TestState for record_from_state tests."""
    return TestState(
        words=(WordEntry(expected="the", typed=(TypedChar("t", "t", "correct"),), submitted=True),),
        current_index=0,
        started_at=0.0,
        ended_at=duration,
        duration_s=duration,
        mode="time",
        finished=True,
        raw_per_second=tuple(samples),
    )


def _summary(wpm=80.0, acc=95.0) -> Summary:
    return Summary(
        wpm=wpm, raw_wpm=wpm + 5, accuracy=acc, consistency=70.0,
        correct_chars=400, incorrect_chars=20, extra_chars=5,
    )


def _config(mode="time", duration=60, words=0, lang="english-1k") -> Config:
    return Config(
        mode=mode,
        duration_s=float(duration),
        word_count=words,
        language=lang,
        show_live_wpm=True,
    )


def test_record_from_state_populates_all_fields():
    state = _finished_state(duration=60.0, samples=(40.0, 50.0, 60.0))
    summary = _summary(wpm=80.0, acc=96.5)
    config = _config(mode="time", duration=60, lang="english-1k")
    ts = datetime(2026, 5, 7, 19, 14, 2, tzinfo=timezone.utc)

    rec = history.record_from_state(state, summary, config, ts)

    assert rec.ts == "2026-05-07T19:14:02Z"
    assert rec.wpm == 80.0
    assert rec.raw == 85.0
    assert rec.acc == 96.5
    assert rec.consistency == 70.0
    assert rec.mode == "time"
    assert rec.length == 60
    assert rec.language == "english-1k"
    assert rec.punctuation is False
    assert rec.numbers is False
    assert rec.chars == {"correct": 400, "incorrect": 20, "extra": 5, "missed": 0}
    assert rec.duration_s == 60.0
    assert rec.samples == (40.0, 50.0, 60.0)


def test_record_length_uses_word_count_for_words_mode():
    state = _finished_state(duration=12.0)
    summary = _summary()
    config = _config(mode="words", duration=0, words=25, lang="english-200")

    rec = history.record_from_state(state, summary, config, datetime(2026, 5, 7, tzinfo=timezone.utc))

    assert rec.mode == "words"
    assert rec.length == 25
    assert rec.duration_s == 12.0


def test_config_key_from_record():
    state = _finished_state()
    config = _config(mode="time", duration=30, lang="english-200")
    rec = history.record_from_state(state, _summary(), config, datetime(2026, 5, 7, tzinfo=timezone.utc))
    assert history.config_key(rec) == ("time", 30, "english-200", False, False)


def test_config_key_from_config():
    config = _config(mode="words", duration=0, words=50, lang="english-1k")
    assert history.config_key(config) == ("words", 50, "english-1k", False, False)


def test_append_then_load_roundtrip(tmp_path):
    path = tmp_path / "history.jsonl"
    state = _finished_state(samples=(40.0, 50.0))
    rec = history.record_from_state(state, _summary(), _config(), datetime(2026, 5, 7, tzinfo=timezone.utc))

    history.append(rec, path)
    loaded = history.load_all(path)

    assert len(loaded) == 1
    assert loaded[0] == rec


def test_append_appends_not_overwrites(tmp_path):
    path = tmp_path / "history.jsonl"
    rec1 = history.record_from_state(
        _finished_state(), _summary(wpm=70.0), _config(),
        datetime(2026, 5, 7, tzinfo=timezone.utc),
    )
    rec2 = history.record_from_state(
        _finished_state(), _summary(wpm=85.0), _config(),
        datetime(2026, 5, 8, tzinfo=timezone.utc),
    )

    history.append(rec1, path)
    history.append(rec2, path)
    loaded = history.load_all(path)

    assert len(loaded) == 2
    assert {r.wpm for r in loaded} == {70.0, 85.0}


@pytest.mark.skipif(
    hasattr(os, "geteuid") and os.geteuid() == 0,
    reason="chmod-based unwritable test is unreliable when running as root",
)
def test_append_swallows_oserror(tmp_path):
    """Pointing append at an unwritable path must not raise."""
    bad_path = tmp_path / "nope" / "deeper" / "history.jsonl"
    bad_path.parent.mkdir(parents=True)
    bad_path.parent.chmod(0o400)  # read-only
    try:
        rec = history.record_from_state(
            _finished_state(), _summary(), _config(),
            datetime(2026, 5, 7, tzinfo=timezone.utc),
        )
        history.append(rec, bad_path)  # must not raise
    finally:
        bad_path.parent.chmod(0o700)


def test_load_all_missing_file(tmp_path):
    assert history.load_all(tmp_path / "nope.jsonl") == []


def test_load_all_skips_malformed_lines(tmp_path):
    path = tmp_path / "history.jsonl"
    rec = history.record_from_state(
        _finished_state(), _summary(), _config(),
        datetime(2026, 5, 7, tzinfo=timezone.utc),
    )
    history.append(rec, path)
    # Append a garbage line.
    with open(path, "a") as f:
        f.write("this is not json\n")
        f.write("\n")
        f.write('{"this": "lacks required fields"}\n')

    loaded = history.load_all(path)
    assert len(loaded) == 1
    assert loaded[0].wpm == rec.wpm


def test_load_all_defaults_missing_optional_fields(tmp_path):
    """Records without punctuation/numbers/samples get safe defaults."""
    path = tmp_path / "history.jsonl"
    minimal = {
        "ts": "2026-05-07T00:00:00Z",
        "wpm": 80.0, "acc": 95.0,
        "mode": "time", "length": 60, "language": "english-1k",
    }
    import json
    with open(path, "w") as f:
        f.write(json.dumps(minimal) + "\n")

    loaded = history.load_all(path)
    assert len(loaded) == 1
    assert loaded[0].punctuation is False
    assert loaded[0].numbers is False
    assert loaded[0].samples == ()


def test_load_all_skips_record_with_non_dict_chars(tmp_path):
    """A record where 'chars' is not a dict must be skipped, not stored
    with malformed content that would crash later consumers."""
    path = tmp_path / "history.jsonl"
    bad = {
        "ts": "2026-05-07T00:00:00Z",
        "wpm": 80.0, "acc": 95.0,
        "mode": "time", "length": 60, "language": "english-1k",
        "chars": "not a dict",
    }
    import json
    with open(path, "w") as f:
        f.write(json.dumps(bad) + "\n")

    assert history.load_all(path) == []
