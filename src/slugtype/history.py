"""History persistence and personal-best queries. JSONL-backed."""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Tuple

from slugtype.state import TestState

ConfigKey = Tuple[str, int, str, bool, bool]


@dataclass(frozen=True)
class Record:
    ts: str                          # ISO 8601 UTC, e.g. "2026-05-07T19:14:02Z"
    wpm: float
    raw: float
    acc: float
    consistency: float
    mode: str                        # "time" | "words"
    length: int                      # duration_s for time mode, word_count for words
    language: str
    punctuation: bool                # always False in v0.3a; reserved for v1.0
    numbers: bool                    # always False in v0.3a; reserved for v1.0
    chars: dict
    duration_s: float
    samples: tuple = ()              # per-second raw WPM


def _config_length(config) -> int:
    if config.mode == "time":
        return int(config.duration_s)
    return int(config.word_count)


def record_from_state(state: TestState, summary, config, ts: datetime) -> Record:
    """Build a Record from a finished TestState + Summary + Config + timestamp."""
    duration = (
        (state.ended_at - state.started_at)
        if state.started_at is not None and state.ended_at is not None
        else 0.0
    )
    return Record(
        ts=ts.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        wpm=summary.wpm,
        raw=summary.raw_wpm,
        acc=summary.accuracy,
        consistency=summary.consistency,
        mode=config.mode,
        length=_config_length(config),
        language=config.language,
        punctuation=getattr(config, "punctuation", False),
        numbers=getattr(config, "numbers", False),
        chars={
            "correct": summary.correct_chars,
            "incorrect": summary.incorrect_chars,
            "extra": summary.extra_chars,
            "missed": 0,
        },
        duration_s=duration,
        samples=tuple(state.raw_per_second),
    )


def config_key(record_or_config) -> ConfigKey:
    """Build the PB key tuple from a Record or Config. Tuple shape:
    (mode, length, language, punctuation, numbers).
    """
    if isinstance(record_or_config, Record):
        r = record_or_config
        return (r.mode, r.length, r.language, r.punctuation, r.numbers)
    c = record_or_config
    return (
        c.mode,
        _config_length(c),
        c.language,
        getattr(c, "punctuation", False),
        getattr(c, "numbers", False),
    )


def _record_to_json(record: Record) -> dict:
    return {
        "ts": record.ts,
        "wpm": record.wpm,
        "raw": record.raw,
        "acc": record.acc,
        "consistency": record.consistency,
        "mode": record.mode,
        "length": record.length,
        "language": record.language,
        "punctuation": record.punctuation,
        "numbers": record.numbers,
        "chars": record.chars,
        "duration_s": record.duration_s,
        "samples": list(record.samples),
    }


def _record_from_json(d: dict) -> Optional[Record]:
    """Build a Record from a JSON dict; return None if required fields are
    missing or malformed. Optional fields default to safe values.
    """
    try:
        return Record(
            ts=str(d["ts"]),
            wpm=float(d["wpm"]),
            raw=float(d.get("raw", 0.0)),
            acc=float(d["acc"]),
            consistency=float(d.get("consistency", 100.0)),
            mode=str(d["mode"]),
            length=int(d["length"]),
            language=str(d["language"]),
            punctuation=bool(d.get("punctuation", False)),
            numbers=bool(d.get("numbers", False)),
            chars=d.get("chars", {"correct": 0, "incorrect": 0, "extra": 0, "missed": 0}),
            duration_s=float(d.get("duration_s", 0.0)),
            samples=tuple(d.get("samples", ())),
        )
    except (KeyError, ValueError, TypeError):
        return None


def append(record: Record, path: Path) -> None:
    """Best-effort: write one JSON line to `path`. Swallows OSError so a
    finished test always reaches the result screen.
    """
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a") as f:
            json.dump(_record_to_json(record), f)
            f.write("\n")
    except OSError:
        pass


def load_all(path: Path) -> list[Record]:
    """Load all records from `path`. Returns [] for missing file. Skips
    malformed JSON lines individually.
    """
    if not path.exists():
        return []
    records: list[Record] = []
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                except json.JSONDecodeError:
                    continue
                rec = _record_from_json(d)
                if rec is not None:
                    records.append(rec)
    except OSError:
        return []
    return records
