# slugtype

A terminal typing test in the style of Monkeytype.

## Install (dev)

```bash
pip install -e .[dev]
```

## Run

```bash
slugtype                # 60-second english-1k test
slugtype --time 30      # 30-second test
slugtype --words 25     # 25-word test
slugtype --language english-200
slugtype --no-live-wpm  # hide the live wpm counter
```

## Stats

slugtype reports four numbers at the end of every test:

- **wpm** — net words per minute: `(correct word chars + correct spaces between fully-correct words) * 60 / test_seconds / 5`
- **raw** — raw words per minute (counts all keystrokes including incorrect)
- **acc** — character-level accuracy: `100 * correct_chars / (correct_chars + incorrect_chars)`
- **consistency** — 1σ stability of per-second raw wpm (higher is more consistent)

## History

Completed tests are appended to a JSONL history file:

- macOS: `~/Library/Application Support/slugtype/history.jsonl`
- Linux: `$XDG_DATA_HOME/slugtype/history.jsonl` (default `~/.local/share/slugtype/history.jsonl`)

Personal-best detection compares against this file. Delete it to reset PBs.

## Keys

| Key | Action |
|---|---|
| Tab, Ctrl-R | Restart with the same config |
| Esc | Open the settings menu (or close the result screen) |
| n | (Result screen) Open settings menu |
| q | (Result screen) Quit |
| Ctrl-C | Abort immediately |
