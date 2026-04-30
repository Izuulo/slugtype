"""Fetch word lists from upstream and write to src/slugtype/data/.

Dev tool only — not shipped at runtime. Run from the repo root:

    python scripts/fetch_word_lists.py
"""
from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path


SOURCES = {
    "english-1k": "https://raw.githubusercontent.com/monkeytypegame/monkeytype/master/frontend/static/languages/english_1k.json",
}

DEST = Path(__file__).resolve().parent.parent / "src" / "slugtype" / "data"


def fetch_and_write(name: str, url: str) -> int:
    print(f"Fetching {name} from {url}", file=sys.stderr)
    req = urllib.request.Request(url, headers={"User-Agent": "slugtype-dev/0.2"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        payload = json.load(resp)
    raw_words = payload.get("words", [])
    # Filter to lowercase ASCII alphabetic words; preserve order.
    words = []
    seen = set()
    for w in raw_words:
        normalised = w.lower()
        if not normalised.isascii() or not normalised.isalpha():
            continue
        if normalised in seen:
            continue
        seen.add(normalised)
        words.append(normalised)
    DEST.mkdir(parents=True, exist_ok=True)
    out_path = DEST / f"{name}.txt"
    out_path.write_text("\n".join(words) + "\n", encoding="utf-8")
    print(f"Wrote {len(words)} words to {out_path}", file=sys.stderr)
    return len(words)


def main() -> int:
    for name, url in SOURCES.items():
        fetch_and_write(name, url)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
