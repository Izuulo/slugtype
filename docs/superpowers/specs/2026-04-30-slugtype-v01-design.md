---
project: slugtype
title: v0.1 Initial Build Design
created: 2026-04-30
updated: 2026-04-30
kind: design
status: approved
source_prd: docs/2026-04-30-initial-prd.md
---

# slugtype v0.1 — Initial Build Design

> Source PRD: `docs/2026-04-30-initial-prd.md` (originally written for `monketerm`; this project was renamed to `slugtype` on 2026-04-30). Where the PRD says `monketerm`, read `slugtype` everywhere — package name, console-script, history paths, window title.

## 1. Goal

Ship the **v0.1 walking skeleton** from PRD §13: the smallest thing that types. The user runs `slugtype`, sees three lines of words, types until the 60-second timer expires, and gets a one-line `wpm: X  acc: Y%` summary on stdout. Nothing more.

This design also maps the path through v0.2 → v1.0 so subsequent milestones know where to plug in without re-architecting.

## 2. Scope

### In scope (v0.1)

- CLI: `slugtype [--time SECONDS] [--words N]` (mutually exclusive, default `--time 60`)
- Curses screen: top bar, three word lines with caret, bottom bar (countdown + "press any key to start")
- Bundled word list: `english-200.txt`
- Input: letters, space, backspace, Ctrl-C
- Stats: `wpm`, `accuracy` displayed; `raw_wpm` computed and tested but not displayed (lands on result screen at v0.2). All pure functions over finalized state.
- Tests: `test_stats.py`, `test_state.py`, `test_words.py` — all run without a TTY
- Module seams in place: `state.py` ↔ `render.py` split, `input.py` Key enum, `theme.py` palette resolver

### Deferred to later milestones

- v0.2: live wpm, full result screen, raw + consistency stats, `english-1k.txt`, tab restart, esc menu
- v0.3: per-second graph, `history.jsonl`, PB detection, history view, `paths.py`, `history.py`
- v1.0: punctuation/numbers, quote mode, color fallbacks, SIGWINCH/resize handling, saved config
- v1.1+: themes, replay, additional languages, custom word lists

## 3. Project structure

```
slugtype/
├── pyproject.toml              # setuptools>=61, console_script: slugtype
├── README.md                   # install, run, how wpm/acc are computed
├── CLAUDE.md                   # per-project Claude rules
├── docs/
│   ├── 2026-04-30-initial-prd.md
│   └── superpowers/specs/
│       └── 2026-04-30-slugtype-v01-design.md   # this file
├── src/slugtype/
│   ├── __init__.py             # __version__ = "0.1.0"
│   ├── cli.py                  # argparse → run.run_test(config)
│   ├── run.py                  # curses event loop
│   ├── state.py                # TestState + apply_keypress (pure)
│   ├── stats.py                # wpm + accuracy (pure)
│   ├── words.py                # load + sample (pure with seeded RNG)
│   ├── render.py               # draw_top_bar / draw_word_stream / draw_bottom_bar
│   ├── input.py                # Key enum + curses keycode → Key
│   ├── theme.py                # single serika-dark palette resolver
│   ├── terminal.py             # alt-screen, raw mode, restore-on-exit, size guard
│   └── data/
│       └── english-200.txt
└── tests/
    ├── test_stats.py
    ├── test_state.py
    └── test_words.py
```

`history.py`, `paths.py`, `english-1k.txt`, `quotes.json`, and `scripts/fetch_word_lists.py` are **not** created at v0.1. They appear in their respective milestones.

## 4. Module responsibilities (v0.1)

### `cli.py`

argparse with `--time SECONDS` and `--words N` (mutually exclusive). Validates: `--time` ∈ {15, 30, 60, 120}, `--words` ∈ {10, 25, 50, 100}. Builds a `Config` dataclass and calls `run.run_test(config)`. No curses imports here.

### `run.py`

Owns the curses event loop. Sequence:

1. `with terminal.session() as window:` — context manager handles alt-screen, raw mode, cursor hide, signal handlers, and ≥60×15 size guard. On exit (normal or exceptional), it restores the terminal.
2. Inside the context:
   - `words.sample(config) -> tuple[str, ...]` — generate the word list
   - Build initial `TestState`
   - Loop at ~60 Hz:
     - Poll input via `window.getch()` with short timeout
     - If a key arrived:
       - `Key.CTRL_C` → set a local `aborted=True` flag and break (no result printed)
       - any other key → translate via `input.translate(keycode) -> Key`, call `state.apply_keypress(state, key, now)`
     - If `state.started_at is not None` and `now - last_tick >= 1.0`: `state = state.tick(now)`
     - If state changed since last frame: `render.draw(window, state, theme)`
     - If `state.finished`: set `state = state._replace(ended_at=now)` and break
3. After the context exits and the terminal is restored:
   - If `aborted` → return without printing
   - Else → compute `final = stats.summary(state)` and print `wpm: X  acc: Y%` to stdout

Ctrl-C delivered as a signal (rather than as a byte through raw mode) propagates as `KeyboardInterrupt`; the context manager's `__exit__` still runs, the `aborted` path applies, and no result is printed.

### `state.py` — pure, no I/O

```python
@dataclass(frozen=True)
class TypedChar:
    expected: str
    typed: str
    category: Literal["correct", "incorrect", "extra"]

@dataclass(frozen=True)
class WordEntry:
    expected: str
    typed: tuple[TypedChar, ...]   # length may exceed expected (extras)
    submitted: bool                # True after space submission

@dataclass(frozen=True)
class TestState:
    words: tuple[WordEntry, ...]
    current_index: int
    started_at: float | None       # None until first keypress
    ended_at: float | None         # set by tick (time mode) or apply_space on last word (words mode)
    duration_s: float              # 60.0 in v0.1 time-mode default; ignored in words mode
    mode: Literal["time", "words"]
    finished: bool                 # True iff ended_at is not None

def initial_state(words: tuple[str, ...], mode: str, duration_s: float) -> TestState
def apply_keypress(state: TestState, key: Key, now: float) -> TestState
def tick(state: TestState, now: float) -> TestState
```

`apply_keypress` dispatches to internal helpers `_apply_char`, `_apply_space`, `_apply_backspace`. Each returns a new state. Rules:

- **First keypress** sets `started_at = now`. Backspace and space-at-word-start are **not** considered first keypresses (they're no-ops).
- **Char** is classified `correct` if `index < len(expected) and ch == expected[index]`, `incorrect` if `index < len(expected) and ch != expected[index]`, `extra` if `index >= len(expected)`.
- **Space** at word start (no chars typed in current word) is a no-op. Otherwise sets `submitted=True` and increments `current_index`. In `words` mode, submitting the last word sets `finished=True` and `ended_at=now`.
- **Backspace** pops the last `TypedChar` from the current word's `typed`. No-op if empty. Cannot cross word boundaries.
- **Tick** in `time` mode sets `finished=True` and `ended_at=started_at + duration_s` when `now - started_at >= duration_s`. In `words` mode, tick is a no-op (the test ends only via space-on-last-word).

### `stats.py` — pure functions over finalized state

```python
@dataclass(frozen=True)
class Summary:
    wpm: float
    raw_wpm: float        # populated at v0.2; v0.1 may compute but doesn't display
    accuracy: float
    correct_chars: int
    incorrect_chars: int
    extra_chars: int

def summary(state: TestState) -> Summary
def wpm(state: TestState) -> float
def accuracy(state: TestState) -> float
```

Formulas per PRD §6:

- `wpm = (correct_word_chars + correct_spaces) * 60 / test_seconds / 5`
  - `correct_word_chars` = total chars across **fully correct** submitted words (every char `correct`, zero `extra`s)
  - `correct_spaces` = count of submission-spaces between two **adjacent fully correct** submitted words
  - `test_seconds` = `ended_at - started_at`. In time mode this equals `duration_s` because `tick` sets `ended_at = started_at + duration_s`. In words mode it's the wall-clock elapsed time. If `started_at` is `None` (no keys ever pressed), wpm is `0.0`.
- `accuracy = 100 * correct_chars / (correct_chars + incorrect_chars)`; returns `100.0` when no chars typed
- `raw_wpm` = `(correct + incorrect + extra + spaces_submitted) * 60 / test_seconds / 5` — computed and stored on `Summary` at v0.1, not displayed in the v0.1 stdout line. Test coverage for raw_wpm lives in `test_stats.py` from v0.1 onward.

### `words.py` — pure given a seeded RNG

```python
def load(name: str) -> tuple[str, ...]            # reads data/{name}.txt
def sample(words: tuple[str, ...], n: int, rng: random.Random) -> tuple[str, ...]
```

For v0.1, `n` is large enough to fill 60s of typing for a fast user — sample 200 words (i.e., the full english-200 list, sampled with replacement). `rng` is seeded by default from `random.SystemRandom()` but tests inject a deterministic `random.Random(seed)`.

Punctuation/number injection lives here at v1.0 as separate transform functions; v0.1 does not call them.

### `render.py` — pure(ish) over a curses window

```python
def draw(window, state: TestState, theme: Theme) -> None
def draw_top_bar(window, config_label: str, theme: Theme) -> None
def draw_word_stream(window, state: TestState, theme: Theme) -> None
def draw_bottom_bar(window, state: TestState, theme: Theme) -> None
```

Each function takes the curses window plus a snapshot of state — no global state. The word stream renders the current word and the next two lines of upcoming words; already-completed words scroll out of view as the user advances. Caret is drawn as a block (or underline if the terminal lacks block support) at the cursor position inside the current word.

For v0.1, **no result screen** — the result is one line on stdout after curses tears down.

### `input.py`

```python
class Key(Enum):
    CHAR    # carries a `value: str` field
    SPACE
    BACKSPACE
    CTRL_C
    RESIZE
    UNKNOWN  # ignored at v0.1

def translate(keycode: int) -> Key
```

At v0.1 the only keys we care about are letters, space, backspace, Ctrl-C, and resize. Escape-sequence buffering for arrow keys arrives at v0.2 with the menu.

### `theme.py`

```python
@dataclass(frozen=True)
class Theme:
    fg_correct: int      # curses color pair index
    fg_dim: int
    fg_caret: int
    fg_error: int

def resolve() -> Theme   # always returns serika-dark in v0.1
```

256/16-color fallback logic arrives at v1.0; v0.1 assumes 24-bit color is available and uses serika-dark as published by Monkeytype.

### `terminal.py`

```python
@contextmanager
def session() -> Iterator[curses.window]
```

Mirrors `worldview`'s pattern: enter alt-screen, raw mode, hide cursor; on exit restore everything. Verifies ≥60×15 at startup; if smaller, exits before entering alt-screen with a stderr message. Resize handling at v0.1 is shallow: curses delivers `KEY_RESIZE` through `getch()`, `input.translate` maps it to `Key.RESIZE`, and `run.py` triggers a redraw on the next frame. No custom signal handler is installed. Full resize-recovery (pause + "too small" overlay) lands at v1.0.

## 5. Data flow (one frame)

```
keypress
  → terminal getch()
  → input.translate(keycode) → Key
  → state.apply_keypress(state, key, now) → new state
  → render.draw(window, new_state, theme)

tick (every ~1s after first keypress)
  → state.tick(state, now) → new state
  → render.draw(window, new_state, theme)

state.finished = True
  → break loop
  → terminal.teardown()
  → stats.summary(state) → Summary
  → print "wpm: X  acc: Y%"
```

State flows one direction. Render reads state, never writes it. Stats read state, never write it. The only mutation is `state = state.apply_keypress(...)` inside the loop.

## 6. Error handling (v0.1)

- **Ctrl-C anywhere:** `terminal.session()` context manager restores the terminal in `__exit__`. No partial result is printed.
- **Terminal too small at startup:** print to stderr `"slugtype: needs at least 60x15, got {cols}x{rows}"`, exit 1. Don't enter alt-screen.
- **Resize mid-test:** redraw on next frame. Pause + "too small" overlay deferred to v1.0.
- **Empty word list (shouldn't happen):** `words.load()` raises if file missing or empty; caught in `cli.py` and printed as `"slugtype: word list 'english-200' is empty or missing"`.
- **`TERM` not set:** curses initialization will fail; catch in `cli.py` and print a clear message (`"slugtype: TERM not set"`). Full `TERM=dumb` detection lands at v1.0.
- **Keys we don't handle:** `Key.UNKNOWN` is a no-op. Unknown bytes don't crash.

## 7. Testing strategy

**Hard rule per PRD §7.3 and the `worldview` precedent:** every test runs without a TTY. Tests live in `tests/` and import from `src/slugtype/...`.

### `test_stats.py`

- `wpm` formula on hand-crafted `TestState` examples:
  - All correct, no extras → matches PRD §6.1 expected value
  - All incorrect → wpm = 0
  - Mixed correct/incorrect words → only fully-correct words count
  - `correct_spaces` term: two fully-correct adjacent words contribute one space; an incorrect word in between breaks the chain
  - Empty state (nothing typed) → wpm = 0
- `accuracy` formula:
  - All correct → 100.0
  - All incorrect → 0.0
  - Half-half → 50.0
  - Empty → 100.0 (PRD §6.3 default)
- `raw_wpm` exists and counts correct + incorrect + extras + spaces

### `test_state.py`

For each transition, build state, apply keys, assert the new state:

- First char sets `started_at`; backspace before any key does not
- Correct char → `category="correct"`
- Incorrect char → `category="incorrect"`
- Extra char (typed past expected length) → `category="extra"`
- Backspace pops one `TypedChar`; cannot pop past zero
- Space at word start → no-op
- Space after typing → submits word, advances `current_index`
- Tick after `duration_s` → `finished=True` in time mode
- Submitting last word in `words` mode → `finished=True`

### `test_words.py`

- `load("english-200")` returns a tuple of 200 lowercase ASCII words
- `sample(words, n, rng)` with a seeded RNG is deterministic
- `sample` with `n > len(words)` works (with replacement)
- `load` raises a clear error for a missing file

### Not tested at v0.1

- `render.py` — golden-string tests against a window-shaped recorder land at v0.2 once `draw_result_screen` exists
- `terminal.py` — exercised manually; CI smoke test arrives at v1.0
- `cli.py` — argparse is thin; tested via `subprocess` smoke test at v0.2 if needed

### Test discipline

- No test imports `curses`. If a test needs to verify rendering, it uses a recorder fake.
- No test reads or writes the user's home directory. (When `history.py` lands, its tests use `tmp_path`.)
- Time-dependent tests pass `now` explicitly; never call `time.time()` in production code without taking it as a parameter.

## 8. Acceptance for v0.1

The walking skeleton is done when:

1. `slugtype` launches in the terminal, shows three lines of english-200 words, and a caret on the first character.
2. Typing letters advances the caret; correct chars render in foreground, incorrect in red, extras in dim red.
3. Space submits a word and advances. Backspace deletes within the current word.
4. After 60 seconds (or immediately on Ctrl-C), curses tears down and the terminal returns to the user's prompt at column 0 with the cursor visible. No screen artifacts.
5. On natural completion (timer expires), the program prints `wpm: <int>  acc: <float>%` to stdout and exits 0.
6. `pytest` passes — at minimum: `test_stats.py` covers wpm + accuracy formulas, `test_state.py` covers correct/incorrect/extra/backspace/space/tick transitions, `test_words.py` covers load + sample.
7. `pip install -e .` from a fresh clone succeeds with no runtime dependencies beyond stdlib.

## 9. Milestone roadmap (informational — not v0.1 work)

### v0.2 — full test loop

- `stats.py`: add `consistency` (Kogasa) and `live_wpm(state, now)`. `TestState` gains `raw_per_second: tuple[float, ...]`; `tick` appends a sample once per second.
- `state.py`: `apply_tab(state) -> TestState` returns a fresh state with the same config and a new word sample.
- `render.py`: `draw_bottom_bar` shows live wpm. New `draw_result_screen(summary)` with the four headline stats. New `draw_menu(...)` modal.
- `input.py`: `Key.TAB`, `Key.ESC`, arrow keys; escape-sequence buffering.
- `cli.py`: `--language {english-200,english-1k}`, `--no-live-wpm`. Bundle `english-1k.txt`.
- `tests/`: `test_state.py` covers tab restart; `test_stats.py` adds raw + consistency; `test_render.py` golden-strings the bottom bar against a recorder fake.

### v0.3 — graph + history

- New `paths.py` (XDG/macOS resolution, called once at startup).
- New `history.py`: JSONL append at `<data>/slugtype/history.jsonl`, PB query by config key.
- `render.py`: `draw_result_graph(samples, pb_wpm | None)` using box-drawing chars; PB dashed line if applicable. Scrollable history view.
- `run.py`: on test finish, build the JSONL record (PRD §10.1) and append. PB validation per PRD §5.5 (≥1s duration, ≥75% acc).
- `tests/`: `test_history.py` covers append, PB lookup, validation gates. Uses `tmp_path` fixture; never the real path.

### v1.0 — polish & full feature set

- `words.py`: `inject_punctuation(words, rng)` and `inject_numbers(words, rng)`. Quote mode loads from `data/quotes.json` (licensing decision required first — PRD §15) and runs as a single concatenated buffer.
- `theme.py`: 256/16-color fallback based on `$COLORTERM` / `$TERM` / `curses.COLORS`.
- `terminal.py`: SIGWINCH pause + "too small" overlay; `TERM=dumb` exits cleanly.
- `cli.py`: `--mode`, `--punctuation`, `--numbers`, `--history`. Saved config at `~/.config/slugtype/config.json` (or platform equiv).
- Performance: if redraw cost dominates at 200wpm, throttle render to one-per-key + one-per-second tick (state still updates per key).
- `paths.py`: extend to resolve config path.

### Cross-cutting invariants

- The `state.py` ↔ `render.py` split is non-negotiable across all milestones. New features extend dataclass fields and add render functions; never reach into curses from `state.py` or `stats.py`.
- Each milestone's tests run without a TTY.
- Each milestone is independently releasable — no half-shipped features.

## 10. Open questions deferred (not blockers for v0.1)

- Quote dataset licensing — settle before v1.0 quote mode (PRD §15)
- Live wpm default on/off — settle at v0.2 (PRD §15)
- Quiet mode existence — settle at v1.0 (PRD §15)
- Tab vs. enter for restart — settle at v0.2 (PRD §15)

## 11. Out-of-scope (explicit)

- Online accounts, leaderboards, syncing
- Themes (v1.1+)
- Funboxes, layoutfluid, polyglot
- Multi-language word lists beyond English (architecture allows it; not built)
- Mouse support
- Windows support (best-effort, not a release blocker)
- Replay / input-history scrubbing (v2)
