"""Argparse and program entry point. No curses imports here."""
from __future__ import annotations

import argparse
import sys
from typing import Optional, Sequence

from slugtype import __version__
from slugtype.run import Config, run_test
from slugtype.terminal import TerminalTooSmallError


VALID_TIMES = (15, 30, 60, 120)
VALID_WORDS = (10, 25, 50, 100)
VALID_LANGUAGES = ("english-200", "english-1k")
DEFAULT_TIME = 60
DEFAULT_LANGUAGE = "english-1k"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="slugtype", description="A terminal typing test.")
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--time",
        type=int,
        choices=VALID_TIMES,
        help=f"time-mode duration in seconds (one of {VALID_TIMES}); default {DEFAULT_TIME}",
    )
    group.add_argument(
        "--words",
        type=int,
        choices=VALID_WORDS,
        help=f"words-mode target (one of {VALID_WORDS})",
    )
    parser.add_argument(
        "--language",
        choices=VALID_LANGUAGES,
        default=DEFAULT_LANGUAGE,
        help=f"word list to use (default: {DEFAULT_LANGUAGE})",
    )
    parser.add_argument(
        "--no-live-wpm",
        action="store_true",
        help="hide the live wpm counter during the test",
    )
    parser.add_argument("--version", action="version", version=f"slugtype {__version__}")
    return parser


def _config_from_args(args: argparse.Namespace) -> Config:
    show_live_wpm = not args.no_live_wpm
    if args.words is not None:
        return Config(
            mode="words",
            duration_s=0.0,
            word_count=args.words,
            language=args.language,
            show_live_wpm=show_live_wpm,
        )
    duration = args.time if args.time is not None else DEFAULT_TIME
    return Config(
        mode="time",
        duration_s=float(duration),
        word_count=0,
        language=args.language,
        show_live_wpm=show_live_wpm,
    )


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    config = _config_from_args(args)

    try:
        summary = run_test(config)
    except TerminalTooSmallError as e:
        print(str(e), file=sys.stderr)
        return 1
    except FileNotFoundError as e:
        print(f"slugtype: word list missing: {e}", file=sys.stderr)
        return 1
    except ValueError as e:
        print(f"slugtype: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        # Catches curses.error (TERM not set / TERM=dumb) and other unexpected
        # terminal-init failures. Print a clear message and exit non-zero
        # rather than leaking a traceback into a half-restored terminal.
        print(f"slugtype: terminal error: {e}", file=sys.stderr)
        return 1

    if summary is None:
        return 0  # aborted; nothing to print

    print(f"wpm: {round(summary.wpm)}  acc: {summary.accuracy:.1f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
