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
