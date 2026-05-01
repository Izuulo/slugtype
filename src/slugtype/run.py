"""High-level test orchestration: setup terminal, run loop, print result."""
from __future__ import annotations

import random
import time
from dataclasses import dataclass
from typing import Optional

from slugtype import render, stats, words
from slugtype.input import KeyKind, translate
from slugtype.state import TestState, apply_keypress, append_sample, initial_state, tick
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
    """Run tests in a loop, supporting tab restart. Returns the last summary
    on natural exit, or None if the user aborted (Ctrl-C).
    """
    rng = random.Random()
    aborted = False
    last_summary: Optional[stats.Summary] = None

    try:
        with session() as window:
            theme = init_pairs()
            window.timeout(50)

            while True:
                state = _build_initial_state(config, rng)
                label = _config_label(config)
                last_tick = 0.0
                typed_at_last_sample = 0
                init_now = time.monotonic()
                render.draw(window, state, theme, label, init_now, _live_wpm_for_config(state, init_now, config))

                restart_requested = False
                while True:
                    now = time.monotonic()

                    keycode = window.getch()
                    if keycode != -1:
                        key = translate(keycode)
                        if key.kind is KeyKind.CTRL_C:
                            aborted = True
                            break
                        if key.kind is KeyKind.TAB:
                            restart_requested = True
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
                        chars_now = sum(len(w.typed) for w in state.words) + sum(1 for w in state.words if w.submitted)
                        delta_chars = chars_now - typed_at_last_sample
                        typed_at_last_sample = chars_now
                        sample_wpm = delta_chars * 60.0 / 5.0
                        new_state = append_sample(new_state, sample_wpm)
                        state = new_state
                        render.draw(window, state, theme, label, now, _live_wpm_for_config(state, now, config))

                    if state.finished:
                        break

                if aborted:
                    break
                if restart_requested:
                    continue  # outer while: build a fresh state and run again

                # Test finished naturally — show result screen.
                summary = stats.summary(state)
                last_summary = summary
                render.draw_result_screen(window, state, summary, label, theme)
                window.timeout(-1)
                action = "exit"
                while True:
                    keycode = window.getch()
                    if keycode == -1:
                        continue
                    key = translate(keycode)
                    if key.kind is KeyKind.RESIZE:
                        render.draw_result_screen(window, state, summary, label, theme)
                        continue
                    if key.kind is KeyKind.TAB:
                        action = "restart"
                        break
                    # Any other key exits.
                    break
                window.timeout(50)

                if action == "restart":
                    continue
                break
    except KeyboardInterrupt:
        aborted = True
    except TerminalTooSmallError:
        raise

    if aborted:
        return None
    return last_summary
