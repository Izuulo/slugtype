"""Platform-aware data directory resolution. No I/O at import time."""
from __future__ import annotations

import os
import sys
from pathlib import Path


def data_dir() -> Path:
    """Return the slugtype data directory, creating it if missing.

    macOS: ~/Library/Application Support/slugtype/
    Linux: $XDG_DATA_HOME/slugtype/ or ~/.local/share/slugtype/

    If directory creation fails (read-only fs, permission denied), the path
    is still returned; downstream callers swallow write errors.
    """
    if sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        xdg = os.environ.get("XDG_DATA_HOME")
        base = Path(xdg) if xdg else Path.home() / ".local" / "share"
    path = base / "slugtype"
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass
    return path


def history_path() -> Path:
    """Return the path to history.jsonl. Resolves data_dir() each call so
    tests can monkeypatch it without import-time side effects.
    """
    return data_dir() / "history.jsonl"
