"""High-level test orchestration: setup terminal, run loop, print result."""
from __future__ import annotations

import random
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from slugtype import history, paths, render, stats, words
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


TIME_CHOICES = (15, 30, 60, 120)
WORDS_CHOICES = (10, 25, 50, 100)
LANGUAGES = ("english-200", "english-1k")


@dataclass
class MenuState:
    mode: str
    time_length: int
    words_count: int
    language: str
    show_live_wpm: bool
    selected: int = 0


def _menu_state_from_config(config: Config) -> MenuState:
    return MenuState(
        mode=config.mode,
        time_length=int(config.duration_s) if config.mode == "time" else TIME_CHOICES[2],
        words_count=config.word_count if config.mode == "words" else WORDS_CHOICES[1],
        language=config.language,
        show_live_wpm=config.show_live_wpm,
    )


def _config_from_menu(menu: MenuState) -> Config:
    if menu.mode == "time":
        return Config(
            mode="time",
            duration_s=float(menu.time_length),
            word_count=0,
            language=menu.language,
            show_live_wpm=menu.show_live_wpm,
        )
    return Config(
        mode="words",
        duration_s=0.0,
        word_count=menu.words_count,
        language=menu.language,
        show_live_wpm=menu.show_live_wpm,
    )


def _menu_items(menu: MenuState) -> list[tuple[str, str]]:
    if menu.mode == "time":
        length_label = "duration"
        length_value = f"{menu.time_length}s"
    else:
        length_label = "words"
        length_value = str(menu.words_count)
    return [
        ("mode", menu.mode),
        (length_label, length_value),
        ("language", menu.language),
        ("live wpm", "on" if menu.show_live_wpm else "off"),
    ]


def _cycle(values, current, direction: int):
    if current not in values:
        return values[0]
    idx = values.index(current)
    return values[(idx + direction) % len(values)]


def _menu_apply_arrow(menu: MenuState, key) -> MenuState:
    if key.kind is KeyKind.UP:
        menu.selected = (menu.selected - 1) % 4
    elif key.kind is KeyKind.DOWN:
        menu.selected = (menu.selected + 1) % 4
    elif key.kind in (KeyKind.LEFT, KeyKind.RIGHT):
        direction = -1 if key.kind is KeyKind.LEFT else 1
        if menu.selected == 0:
            menu.mode = _cycle(("time", "words"), menu.mode, direction)
        elif menu.selected == 1:
            if menu.mode == "time":
                menu.time_length = _cycle(TIME_CHOICES, menu.time_length, direction)
            else:
                menu.words_count = _cycle(WORDS_CHOICES, menu.words_count, direction)
        elif menu.selected == 2:
            menu.language = _cycle(LANGUAGES, menu.language, direction)
        elif menu.selected == 3:
            menu.show_live_wpm = not menu.show_live_wpm
    return menu


def _open_menu(window, theme, current_config: Config) -> Optional[Config]:
    """Show the menu modal. Returns the new Config if Enter was pressed,
    or None if Esc was pressed to cancel.
    """
    menu = _menu_state_from_config(current_config)
    window.timeout(-1)
    try:
        while True:
            render.draw_menu(window, _menu_items(menu), menu.selected, theme)
            keycode = window.getch()
            if keycode == -1:
                continue
            key = translate(keycode)
            if key.kind is KeyKind.ESC or key.kind is KeyKind.CTRL_C:
                return None
            if key.kind is KeyKind.ENTER:
                return _config_from_menu(menu)
            if key.kind is KeyKind.RESIZE:
                continue
            if key.kind in (KeyKind.UP, KeyKind.DOWN, KeyKind.LEFT, KeyKind.RIGHT):
                menu = _menu_apply_arrow(menu, key)
    finally:
        window.timeout(50)


def _finalize(
    state: TestState,
    summary: stats.Summary,
    config: Config,
    now_utc: datetime,
    history_file,
) -> bool:
    """Persist the finished test (if it qualifies) and decide whether it's
    a personal best for its config. Returns ``was_pb``.

    ``history_file`` is a Path; injected so tests can substitute a tmp path.
    """
    if not history.pb_qualifies(state, summary):
        return False

    record = history.record_from_state(state, summary, config, now_utc)
    # Read existing records *before* appending so the new run isn't its own baseline.
    prior = history.load_all(history_file)
    key = history.config_key(record)
    prev_pb = history.pb_for(prior, key)
    was_pb = prev_pb is None or record.wpm > prev_pb.wpm

    history.append(record, history_file)
    return was_pb


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
                        if key.kind is KeyKind.ESC:
                            new_config = _open_menu(window, theme, config)
                            if new_config is not None:
                                config = new_config
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

                # Test finished naturally — persist, decide PB, show result screen.
                summary = stats.summary(state)
                last_summary = summary
                was_pb = _finalize(
                    state, summary, config,
                    datetime.now(timezone.utc),
                    paths.history_path(),
                )
                render.draw_result_screen(window, state, summary, label, theme, was_pb=was_pb)
                # Drain any keypresses queued during the last second of the test
                # so the result screen doesn't get dismissed by a stale key.
                window.nodelay(True)
                while window.getch() != -1:
                    pass
                window.nodelay(False)
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
                    if key.kind is KeyKind.ESC:
                        new_config = _open_menu(window, theme, config)
                        if new_config is not None:
                            config = new_config
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
