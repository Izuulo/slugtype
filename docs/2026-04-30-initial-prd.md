---
project: monketerm
title: Initial PRD
created: 2026-04-30
updated: 2026-04-30
kind: architecture
---

# monketerm — Product Requirements Document

> Audience: Claude Code, implementing this from scratch in `/Users/finnritter/Projects/monketerm/`. This document is the source of truth for v0.1 → v1.0. If something here conflicts with later instructions from Finn, the later instruction wins; update this file in the same edit.

## 1. Vision

A terminal typing test that mimics the look and feel of [Monkeytype](https://monkeytype.com) and produces the same kind of post-test insights (wpm, raw wpm, accuracy, consistency, per-second graph, error breakdown). It is a single command, runs in any modern terminal, and is satisfying to use for short, repeated sessions.

It is not a port of Monkeytype. It is a small, fast, opinionated subset that captures the _experience_ of Monkeytype on a TTY: a clean stream of words, a caret that advances as you type, dimmed upcoming words, brightly visible errors, a live wpm counter, and a final result screen that tells you something useful.

## 2. Goals & non-goals

### Goals

- Feel like Monkeytype within five seconds of launching: words appear, caret blinks, you start typing.
- Match Monkeytype's stat math exactly so a user familiar with the web app reads the same numbers the same way (wpm, raw wpm, accuracy, consistency formulas in §6).
- Run on macOS and Linux with no install step beyond `pip install -e .`.
- Stdlib-only runtime — same constraint as `worldview` ([[projects/worldview/worldview]]).
- Produce a result screen with a per-second wpm/raw graph rendered in the terminal.
- Persist test history locally so progress over time is visible.

### Non-goals (v1)

- Online accounts, leaderboards, or syncing.
- Themes (defer to v1.1).
- Funboxes, layoutfluid, polyglot, or any of Monkeytype's special modes.
- Multi-language word lists beyond English (defer; architecture must allow it).
- Mouse support.
- Windows support (best-effort; not a release blocker).
- Replay / input-history scrubbing (defer to v2).

## 3. Users & primary use cases

One user: a person who wants a quick typing test in a terminal they already have open. Two flows:

1. **Quick test.** `monketerm` → 60s English-1k test → results → `tab` to retry, `q` to quit.
2. **Configured test.** `monketerm --time 30 --words english-200 --punctuation` → same flow with that config.

That's it. No multi-user, no profiles. History is single-user and lives on disk.

## 4. Stack & constraints

### Recommended stack

- **Language:** Python 3.9+
- **TUI:** `curses` from stdlib. No `textual`, no `rich` at runtime. Rationale: matches `worldview`'s stdlib-only-runtime constraint, no install pain, and `curses` is sufficient for what's needed (a single screen, ~3 word lines, a stat bar, a result panel with a sparkline).
- **Packaging:** `pyproject.toml` with `setuptools>=61`. Single `monketerm` console-script entry point.
- **Tests:** `pytest`. Tests must not require a TTY — separate the pure-logic modules (stat math, word generation, run state) from the curses I/O layer so the logic side can be unit-tested without a terminal.

### Hard constraints

- No runtime dependencies beyond Python stdlib. Dev deps (`pytest`, optionally `ruff`) are fine.
- Must restore the terminal on exit, including on Ctrl-C and SIGWINCH (resize). Mirror `worldview`'s alt-screen + cursor restoration pattern.
- Minimum terminal: 60×15. Below that, render a "terminal too small" message with required dimensions.
- 24-bit color is preferred. Fall back gracefully to 256-color and then 16-color if `$COLORTERM` / `$TERM` indicate less.
- All state lives in memory during a run. History is written to disk only at end-of-test.

### Project layout

Match `project-organization.md` defaults:

```
monketerm/
├── pyproject.toml
├── README.md
├── CLAUDE.md                  # per-project Claude rules; treat as authoritative for the project
├── src/monketerm/
│   ├── __init__.py
│   ├── cli.py                 # argparse, entry point, dispatches into run.py
│   ├── run.py                 # high-level test orchestration (start, tick, finish)
│   ├── state.py               # TestState dataclass; pure state transitions
│   ├── stats.py               # wpm/raw/accuracy/consistency math; pure
│   ├── words.py               # word-list loading + sampling; pure
│   ├── render.py              # curses rendering primitives (word lines, stat bar, result panel)
│   ├── input.py               # keypress handling, escape-sequence buffering
│   ├── history.py             # JSONL persistence; load + append
│   ├── theme.py               # palette + color resolution; v1 ships a single default theme
│   ├── data/
│   │   ├── english-200.txt    # 200 most common English words
│   │   ├── english-1k.txt     # 1000 most common
│   │   └── quotes.json        # quote pool (short, medium, long buckets)
│   └── terminal.py            # alt-screen, raw mode, restore on exit, size guard
├── tests/
│   ├── test_stats.py
│   ├── test_words.py
│   ├── test_state.py
│   └── test_history.py
└── scripts/
    └── fetch_word_lists.py    # one-shot dev script; not shipped at runtime
```

## 5. UX spec

### 5.1 Launch screen → test screen

Cold start: `monketerm` → curses takes over, alt-screen activates, you immediately see:

```
 monketerm                                                       60s · english-1k

   the and that have with this from they were said been each what their which
   their about would there could other after first never these think where most
   more some only over very what when much before again right great every

   1:00                                                                     wpm

                                       press any key to start · esc for menu
```

- **Top bar:** app name on the left, current config on the right (test type, length, language).
- **Word stream:** three visible lines, ~80 cols wide, soft-wrapping on word boundaries. Upcoming words rendered dim. Current word's caret blinks.
- **Bottom bar (idle):** countdown / progress on left, "wpm" placeholder on right, hints in the center.
- **First keypress** starts the test. The hint row disappears. A live timer takes over.

### 5.2 During the test

```
 monketerm                                                       0:42 · english-1k

   the and that have with this from they were said been each what their which
                          ^^^^                  ^                    ^^^^^
   their about would there could other after first never these think where most
   more some only over very what when much before again right great every

   0:18                                                                  87 wpm
```

- **Caret:** a single blinking block (or underline if block isn't supported) at the cursor position inside the current word.
- **Typed correct:** rendered in the foreground color (white-ish on dark theme).
- **Typed incorrect:** rendered in red, on the _expected_ character. If the user typed past the word's length, those extra characters render in dim red appended to the word ("extra" chars in Monkeytype parlance).
- **Untyped current word:** rendered in foreground but slightly dimmed.
- **Upcoming words:** rendered dim.
- **Already-completed words:** rendered dim (Monkeytype hides them by scrolling; in the terminal we keep a single past line briefly visible then scroll).
- **Live wpm:** updates once per second. Live counter is a moving average over the elapsed run (same formula as final wpm; the Monkeytype frontend computes this every second).
- **Progress:** `M:SS` countdown for time mode, `n / N` for word-count mode.

### 5.3 Input rules

- **Letters:** advance caret one character. If correct → mark correct; if incorrect → mark incorrect.
- **Space:** submit current word and advance to next. Space at the start of a word is ignored.
- **Backspace:** delete one character within the current word. If the current word's buffer is empty, backspace crosses into the previous word **only if that word had any incorrect, extra, or missed characters** (Monkeytype default). Fully-correct previous words stay locked.
- **Tab:** restart current test with the same config (regenerate words).
- **Esc:** open command menu (see §5.6).
- **Ctrl-C:** exit cleanly, restore terminal.

### 5.4 End-of-test result screen

When the timer hits zero (time mode) or the last word is submitted (word mode):

```
 monketerm — result                                                       60s · english-1k

       wpm              acc              raw              consistency
       87               96.4%            91               74.2%

   60 ┤                          ╭─╮
   45 ┤        ╭─╮      ╭───╮   ╱   ╲   ╭──
   30 ┤   ╭───╯   ╲────╯     ╲─╯     ╲─╯
   15 ┤  ╱
    0 ┼──────────────────────────────────────
      0s          15s          30s          45s          60s

   characters       errors            time            test type
   438 / 18 / 6     12                60s             time · english-1k

   tab restart · n new test · q quit
```

- Top row of stats uses the same labels and order as Monkeytype: wpm, acc, raw, consistency.
- Mid-section is a per-second wpm graph drawn with Unicode box-drawing characters. Two series overlaid: raw (lighter) and net wpm (foreground). If a personal best for this exact config exists, draw a horizontal dashed line at PB-wpm with a small "pb" label.
- Bottom stats:
  - **characters:** `correct / incorrect / extra` (matches Monkeytype's correct/incorrect/extra/missed split — drop "missed" because it's rare in time mode and confusing).
  - **errors:** total submitted incorrect characters across the test.
  - **time:** wall-clock duration of the test.
  - **test type:** mode + language.
- `tab` repeats the same config with new words. `n` opens the menu. `q` quits.

### 5.5 Personal bests

A PB is per-config: `(mode, length, language, punctuation, numbers)` is the key. After a valid result is computed, compare wpm against the local PB for that key. If higher, mark with a `pb` badge on the result screen and update the on-disk store.

Validation rules (mirror Monkeytype's basic checks; we skip server-side anti-cheat):

- Test must run for ≥1 second.
- Accuracy must be ≥75% to count for PB. (Otherwise still saved to history, just not PB-eligible.)
- Test must not be a `tab`-restart of an in-progress run mid-word — only completed runs count.

### 5.6 Command menu (esc)

Esc opens a centered modal listing config options. Arrow keys navigate, enter selects, esc closes. Categories:

- **Mode:** time / words / quote
- **Length:** for time → 15 / 30 / 60 / 120; for words → 10 / 25 / 50 / 100
- **Language:** english-200 / english-1k
- **Punctuation:** off / on (sprinkles `,`, `.`, `!`, `?` and capitalizes ~10% of words; matches Monkeytype)
- **Numbers:** off / on (sprinkles random integers among the words)
- **Show live wpm:** on / off
- **History:** open the history view (see §5.7)

Selecting any option restarts the current test with the new config.

### 5.7 History view

Reachable from the menu. Renders a scrollable table of recent results: date, wpm, acc, raw, consistency, mode, length, language. Up/down to scroll, enter to view that test's full result screen, esc to return.

### 5.8 Visual language

- Single default theme to start. Approximate Monkeytype's "serika dark":
  - background: `#323437`
  - foreground (correct): `#d1d0c5`
  - sub (upcoming, dim): `#646669`
  - main (caret, accents): `#e2b714`
  - error: `#ca4754`
  - sub-alt: `#2c2e31`
- Background is left to the terminal — don't paint a full-screen background, just use the terminal's default. `sub-alt` is used for the modal panels.
- All colors must degrade through 256-color and 16-color tables. Resolved palette lives in `theme.py`; resolution happens once at startup.

## 6. Stat math

Match Monkeytype's frontend formulas exactly. All of these go in `stats.py` and are pure functions over an immutable `TestResult` input.

### 6.1 WPM

```
wpm = (correct_word_chars + correct_spaces) * 60 / test_seconds / 5
```

- A "correctly typed word" is one submitted with all characters matching the expected word and no extras.
- `correct_word_chars` counts characters in those words.
- `correct_spaces` is the number of space-submits between two correctly typed adjacent words.
- Division by 5 normalizes to a standard "word" of 5 characters.

### 6.2 Raw WPM

```
raw_wpm = (all_correct_chars + spaces + incorrect_chars + extra_chars) * 60 / test_seconds / 5
```

Same shape as wpm but counts every character the user typed, including incorrect and extra.

### 6.3 Accuracy

```
accuracy = 100 * correct_chars / (correct_chars + incorrect_chars)
```

If no characters typed → 100% (matches Monkeytype's default for the empty case).

### 6.4 Consistency

The Kogasa function over the per-second raw-wpm series:

```
cv = stdev(raw_per_second) / mean(raw_per_second)
consistency = kogasa(cv)
```

where `kogasa` maps the coefficient of variation onto a 0–100 scale (closer to 100 = more consistent). Reference implementation (matches Monkeytype's `frontend/src/ts/utils/numbers.ts`):

```python
def kogasa(cov: float) -> float:
    return 100 * (1 - math.tanh(cov + (cov ** 3) / 3))
```

### 6.5 Live wpm

Every second during the test, recompute wpm using the formula in §6.1 with `test_seconds = elapsed`. Display rounded to integer. Accumulate the per-second raw value into `raw_per_second` for the consistency calc and the result graph.

### 6.6 Character categories

Track per character in submitted words:

- `correct` — typed character matched expected.
- `incorrect` — typed character did not match expected, within word length.
- `extra` — typed character past the expected word's length (still inside the word, before space).
- `missed` — characters in the expected word that were never typed because the user hit space early.

`accuracy` and `wpm` care about correct/incorrect; `raw` cares about everything except missed; the result-screen "characters" line shows correct/incorrect/extra.

## 7. Architecture

### 7.1 Module responsibilities

- **`cli.py`** — argparse, validate, hand off to `run.run_test(config)`. No curses calls.
- **`run.py`** — owns the curses event loop. Initializes terminal via `terminal.py`, asks `words.py` for a word stream, builds a `TestState`, dispatches keys via `input.py`, calls `render.py` once per frame and once per second for stat updates, calls `stats.py` at end, hands result to `history.py`, then renders the result screen.
- **`state.py`** — `TestState` dataclass: list of expected words, current word index, per-word typed buffer, list of completed words with category breakdown, start time, end time, per-second wpm sample list. Methods are pure: `apply_keypress(state, key) -> state`. No I/O.
- **`stats.py`** — pure. Takes a finalized `TestState` and returns a `TestResult`. Also exposes `live_wpm(state, now)` for the per-second tick.
- **`words.py`** — loads a word list from `data/`, samples N words, optionally injects punctuation and numbers per the config. Pure given a seeded RNG.
- **`render.py`** — pure(ish) over a curses window. One function per region: `draw_top_bar`, `draw_word_stream`, `draw_bottom_bar`, `draw_result_screen`, `draw_menu`. Each takes the window + a snapshot of state and writes; no global state.
- **`input.py`** — translates curses keycodes into a small `Key` enum (`CHAR(c)`, `SPACE`, `BACKSPACE`, `TAB`, `ESC`, `RESIZE`). Buffers escape sequences for arrow keys.
- **`history.py`** — JSONL at `~/.local/share/monketerm/history.jsonl` (or `$XDG_DATA_HOME/monketerm/history.jsonl` if set, falling back to `~/Library/Application Support/monketerm/` on macOS for parity with platform conventions; see §11). One result per line. PB lookup is a linear scan filtered by config key (cheap until tens of thousands of entries; revisit if needed).
- **`terminal.py`** — alt-screen enter/exit, raw mode, cursor hide/show, signal handlers. Mirrors `worldview`'s pattern.
- **`theme.py`** — single default palette today; structured so adding more is a config change later.

### 7.2 Event loop

At ~60Hz (sleep 16ms when idle, shorter when input is pending):

1. Poll for input via `window.getch()` with a short timeout.
2. If a key arrived → `state = state.apply_keypress(key)`. If state transitioned to "finished" → break to result.
3. If 1s has elapsed since last sample → `state = state.tick(now)`; this appends a per-second wpm/raw sample.
4. Redraw if state changed since last frame.

### 7.3 Testability

The split between `state.py` (pure transitions) and `render.py` (curses I/O) is non-negotiable. A test in `test_state.py` should be able to feed a synthetic key sequence to `apply_keypress` and assert the resulting `TestState` without ever opening a TTY. Same for `test_stats.py` — feed a finalized `TestState`, assert `wpm`, `raw`, `accuracy`, `consistency`. Mirror `worldview`'s test-without-TTY discipline.

## 8. Data files

### 8.1 Word lists

- `english-200.txt` — 200 most common English words, one per line, lowercase, no punctuation. Source: the Monkeytype repo's `english.json` (top 200 entries) is a reasonable seed; can be regenerated from any frequency list.
- `english-1k.txt` — 1000 most common English words, same format.
- `scripts/fetch_word_lists.py` regenerates these from a chosen source URL. It's a dev tool, not shipped at runtime.

### 8.2 Quotes

- `quotes.json` — array of `{ "text": str, "source": str, "length": "short"|"medium"|"long" }`. Buckets:
  - short: ≤100 chars
  - medium: 101–300
  - long: >300
- Pull from the Monkeytype quote dataset under their license terms, or seed with public-domain quotes if the license doesn't permit redistribution. **Open question — confirm with Finn before shipping.**

## 9. Configuration & CLI

```
monketerm [options]

Options:
  --mode {time,words,quote}    test mode (default: time)
  --time SECONDS               for time mode: 15 | 30 | 60 | 120 (default: 60)
  --words N                    for words mode: 10 | 25 | 50 | 100 (default: 25)
  --language NAME              english-200 | english-1k (default: english-1k)
  --punctuation                add punctuation + capitalization
  --numbers                    sprinkle numbers
  --no-live-wpm                hide the live wpm counter
  --history                    open history view directly and exit on q
  --version
  --help
```

Config precedence: CLI flag > saved-config file > built-in default.
Saved-config file: `~/.config/monketerm/config.json` (or XDG equivalent). Written when the user changes settings via the in-app menu and confirms.

## 10. Persistence

### 10.1 History format (`history.jsonl`)

One JSON object per line:

```json
{"ts": "2026-04-30T14:32:11Z", "wpm": 87.3, "raw": 91.2, "acc": 96.4, "consistency": 74.2,
 "mode": "time", "length": 60, "language": "english-1k",
 "punctuation": false, "numbers": false,
 "chars": {"correct": 438, "incorrect": 18, "extra": 6, "missed": 0},
 "duration_s": 60.0, "samples": [42, 51, 60, 58, ...]}
```

The `samples` array is per-second raw-wpm values; required for redrawing the per-test graph on the history view.

### 10.2 Personal bests

Computed on demand from history.jsonl. No separate PB file. PB query: filter by config key, take max(wpm).

## 11. Filesystem locations

Pick once and document. Recommended:

- **macOS:** `~/Library/Application Support/monketerm/` for both data and config (matches platform convention).
- **Linux:** `$XDG_DATA_HOME/monketerm/` for `history.jsonl`, `$XDG_CONFIG_HOME/monketerm/` for `config.json`. Falls back to `~/.local/share/monketerm/` and `~/.config/monketerm/`.

Resolve once at startup in a `paths.py` module; never hardcode at call sites.

## 12. Edge cases & gotchas

- **Resize mid-test (SIGWINCH):** clear screen, recompute layout, redraw. The test continues; the timer keeps running. If the new size violates the 60×15 minimum, pause the test and show the "too small" message; resume when the size is restored.
- **Ctrl-C mid-test:** exit cleanly; do _not_ save a partial result.
- **Tab mid-test:** abort current run without saving; start a fresh one with the same config.
- **No input for the first 5s:** Monkeytype shows an "afk" overlay. We can elide this for v1 — just don't start the timer until the first keypress.
- **Empty word stream:** should not happen, but if it does, exit with a clear error rather than enter a 0-length test.
- **Unicode in word lists:** v1 word lists are ASCII. Don't bother with combining marks yet.
- **Very fast typists:** test a 200wpm scenario; the per-frame redraw must keep up. If it doesn't, throttle redraws to one per keypress + one per second tick.
- **TERM not set / dumb terminal:** detect on startup, exit with a clear message.

## 13. Milestones

### v0.1 — walking skeleton (smallest thing that types)

- `cli.py` argparse with `--time` and `--words` only.
- english-200 word list bundled.
- Time mode only, 60s only.
- Curses screen with three word lines, caret advances on correct chars, `space` advances words.
- No live wpm, no result graph — just print final wpm/acc on exit.
- Pure stats module with tests for wpm and accuracy.

### v0.2 — full test loop

- Live wpm + accuracy in the bottom bar.
- Result screen with all four headline stats.
- Per-second sampling for raw + consistency.
- english-1k bundled.
- Tab restart, esc menu (mode + length + language).

### v0.3 — graph + history

- Result-screen sparkline of per-second wpm/raw.
- `history.jsonl` persistence.
- History view (scrollable table).
- PB detection + badge on result screen.

### v1.0 — polish

- Punctuation + numbers options wired through.
- Quote mode.
- Words mode (n-word target).
- 256/16-color fallback paths.
- Resize handling, TERM=dumb guard, all the §12 edge cases.
- Saved config in `config.json`.

### v1.1+ (out of scope for this PRD)

- Themes (multiple palettes selectable from menu).
- Replay / scrub view.
- Additional languages.
- Custom word lists from a file.

## 14. Acceptance for v1

Claude Code can declare v1 done when:

- `monketerm` launches in <100ms on a modern laptop.
- A 60s english-1k test runs to completion, displays a result screen with wpm / acc / raw / consistency / per-second graph, and persists the result to disk.
- The same config opened twice in a row correctly reports the second run as a PB if it's faster.
- `pytest` passes with at least: `test_stats.py` covering all four stat formulas, `test_state.py` covering correct/incorrect/extra/backspace transitions, `test_words.py` covering word generation with and without punctuation/numbers, `test_history.py` covering append + PB lookup.
- Ctrl-C mid-test restores the terminal cleanly with no leftover artifacts (verified by running, hitting Ctrl-C, and confirming the prompt returns at column 0 with the cursor visible).
- README.md documents install, run, the four headline stats, and where history is stored.

## 15. Open questions for Finn

- Quote dataset licensing — pull from Monkeytype's repo, or seed our own?
- Confirm Python + stdlib `curses` is the desired stack. Alternatives considered: Rust + ratatui (faster, more work; mismatched with the rest of the portfolio), Go + bubbletea (clean, but adds a third runtime). Default: Python.
- Should the live wpm counter default on or off? Monkeytype defaults it on; some purists turn it off to focus on raw speed.
- Should v1 ship with a "quiet" mode (no live wpm, no live timer text — pure caret + words) for minimalists?
- Tab vs. enter for restart — Monkeytype uses tab. Confirm fine to mirror.

## Related

- [[projects/monketerm/monketerm]] — main dossier
- [[projects/worldview/worldview]] — sibling terminal CLI; reuse the alt-screen / raw-mode / SIGWINCH pattern, the stdlib-only-runtime constraint, and the no-TTY-required test discipline.

## Changelog

- 2026-04-30: Initial PRD drafted from conversation. Sourced Monkeytype stat formulas (wpm, raw, accuracy, Kogasa consistency) and stack tradeoffs (Python+curses vs Rust+ratatui vs Go+bubbletea) from web research.
