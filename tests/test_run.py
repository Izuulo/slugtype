"""Integration tests for slugtype.run._finalize — persistence + PB decision."""
from dataclasses import replace
from datetime import datetime, timezone

from slugtype import history
from slugtype.run import Config, _finalize
from slugtype.state import TestState, TypedChar, WordEntry, initial_state
from slugtype.stats import Summary


def _state(duration: float = 60.0, samples=()) -> TestState:
    s = initial_state(("the",), "time", duration)
    return replace(
        s,
        started_at=0.0, ended_at=duration, finished=True,
        raw_per_second=tuple(samples),
        words=(WordEntry(expected="the", typed=(TypedChar("t", "t", "correct"),), submitted=True),),
    )


def _summary(wpm=80.0, acc=95.0) -> Summary:
    return Summary(
        wpm=wpm, raw_wpm=wpm + 5, accuracy=acc, consistency=70.0,
        correct_chars=400, incorrect_chars=20, extra_chars=5,
    )


def _config(duration=60) -> Config:
    return Config(
        mode="time", duration_s=float(duration), word_count=0,
        language="english-1k", show_live_wpm=True,
    )


def _now() -> datetime:
    return datetime(2026, 5, 7, 19, 0, 0, tzinfo=timezone.utc)


def test_finalize_writes_one_record(tmp_path):
    path = tmp_path / "history.jsonl"
    state = _state()
    summary = _summary()

    _finalize(state, summary, _config(), _now(), path)

    records = history.load_all(path)
    assert len(records) == 1
    assert records[0].wpm == 80.0


def test_finalize_first_run_is_pb(tmp_path):
    path = tmp_path / "history.jsonl"
    was_pb = _finalize(_state(), _summary(wpm=80.0), _config(), _now(), path)
    assert was_pb is True


def test_finalize_second_run_pb_when_faster(tmp_path):
    path = tmp_path / "history.jsonl"
    _finalize(_state(), _summary(wpm=70.0), _config(), _now(), path)
    was_pb = _finalize(_state(), _summary(wpm=85.0), _config(), _now(), path)
    assert was_pb is True


def test_finalize_second_run_not_pb_when_slower(tmp_path):
    path = tmp_path / "history.jsonl"
    _finalize(_state(), _summary(wpm=85.0), _config(), _now(), path)
    was_pb = _finalize(_state(), _summary(wpm=70.0), _config(), _now(), path)
    assert was_pb is False


def test_finalize_tied_wpm_not_pb(tmp_path):
    """Strict greater-than: ties don't beat the existing PB."""
    path = tmp_path / "history.jsonl"
    _finalize(_state(), _summary(wpm=80.0), _config(), _now(), path)
    was_pb = _finalize(_state(), _summary(wpm=80.0), _config(), _now(), path)
    assert was_pb is False


def test_finalize_short_run_does_not_write(tmp_path):
    path = tmp_path / "history.jsonl"
    state = _state(duration=0.5)  # < 1s
    was_pb = _finalize(state, _summary(), _config(), _now(), path)
    assert was_pb is False
    assert not path.exists()


def test_finalize_low_accuracy_does_not_write(tmp_path):
    path = tmp_path / "history.jsonl"
    was_pb = _finalize(_state(), _summary(acc=50.0), _config(), _now(), path)
    assert was_pb is False
    assert not path.exists()


def test_finalize_pb_per_config_key(tmp_path):
    """A 30s test does not affect 60s PB and vice versa."""
    path = tmp_path / "history.jsonl"
    # 60s run at 90 wpm
    _finalize(_state(), _summary(wpm=90.0), _config(duration=60), _now(), path)
    # 30s run at 70 wpm — should be PB for the 30s key (no prior 30s run)
    was_pb_30 = _finalize(_state(), _summary(wpm=70.0), _config(duration=30), _now(), path)
    assert was_pb_30 is True
