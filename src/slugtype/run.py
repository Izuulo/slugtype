"""High-level test orchestration: setup terminal, run loop, print result."""
from __future__ import annotations

import random
import time
from dataclasses import dataclass
from typing import Optional

from slugtype import render, stats, words
from slugtype.input import KeyKind, translate
from slugtype.state import TestState, apply_keypress, initial_state, tick
from slugtype.terminal import TerminalTooSmallError, session
from slugtype.theme import init_pairs


@dataclass(frozen=True)
class Config:
    mode: str           # "time" or "words"
    duration_s: float   # used when mode == "time"
    word_count: int     # used when mode == "words"
    language: str       # "english-200" at v0.1
    show_live_wpm: bool = True


def _config_label(config: Config) -> str:
    if config.mode == "time":
        return f"{int(config.duration_s)}s · {config.language}"
    return f"{config.word_count} words · {config.language}"


def _live_wpm_for_config(state: TestState, now: float, config: Config) -> Optional[float]:
    if not config.show_live_wpm:
        return None
    return stats.live_wpm(state, now)


def _build_initial_state(config: Config, rng: random.Random) -> TestState:
    word_pool = words.load(config.language)
    if config.mode == "time":
        # Generate enough words to cover even a fast typist: ~250wpm * (duration/60) words.
        target = max(50, int(250 * config.duration_s / 60))
        sample = words.sample(word_pool, target, rng)
        return initial_state(sample, "time", config.duration_s)
    sample = words.sample(word_pool, config.word_count, rng)
    return initial_state(sample, "words", duration_s=0.0)


def run_test(config: Config) -> Optional[stats.Summary]:
    """Run a single test. Returns the summary on natural completion, or None
    if the user aborted (Ctrl-C).
    """
    rng = random.Random()
    state = _build_initial_state(config, rng)
    label = _config_label(config)

    aborted = False
    final_state = state

    try:
        with session() as window:
            theme = init_pairs()
            window.timeout(50)  # ms; getch blocks up to this long
            last_tick = 0.0
            init_now = time.monotonic()
            render.draw(window, state, theme, label, init_now, _live_wpm_for_config(state, init_now, config))

            while True:
                now = time.monotonic()

                keycode = window.getch()
                if keycode != -1:
                    key = translate(keycode)
                    if key.kind is KeyKind.CTRL_C:
                        aborted = True
                        break
                    if key.kind is KeyKind.RESIZE:
                        render.draw(window, state, theme, label, now, _live_wpm_for_config(state, now, config))
                        continue
                    new_state = apply_keypress(state, key, now)
                    if new_state is not state:
                        state = new_state
                        render.draw(window, state, theme, label, now, _live_wpm_for_config(state, now, config))

                if state.started_at is not None and (now - last_tick) >= 1.0:
                    last_tick = now
                    new_state = tick(state, now)
                    state = new_state  # may or may not be the same object; redraw either way to update countdown
                    render.draw(window, state, theme, label, now, _live_wpm_for_config(state, now, config))

                if state.finished:
                    final_state = state
                    break

            # Test finished naturally: show the result screen and wait for a keypress.
            if not aborted:
                summary = stats.summary(final_state)
                elapsed = (final_state.ended_at - final_state.started_at) if final_state.started_at and final_state.ended_at else 0.0
                render.draw_result_screen(window, summary, label, theme, elapsed)
                window.timeout(-1)  # block until a key arrives
                while True:
                    keycode = window.getch()
                    if keycode == -1:
                        continue
                    key = translate(keycode)
                    if key.kind is KeyKind.RESIZE:
                        render.draw_result_screen(window, summary, label, theme, elapsed)
                        continue
                    # Any key (including Ctrl-C) exits.
                    break
    except KeyboardInterrupt:
        aborted = True
    except TerminalTooSmallError:
        # Re-raise so cli.py can print to stderr after teardown.
        raise

    if aborted:
        return None
    return stats.summary(final_state)
