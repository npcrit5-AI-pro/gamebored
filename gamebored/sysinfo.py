"""System info / About screen for GameBored OS."""

import curses
import sys
import time

from . import __version__
from . import storage as storage_mod
from . import ui
from .games import GAMES

TITLE = "About"
DESCRIPTION = "This machine, in numbers"
CONTROLS = "Any key back to menu"


def info_lines(width=80):
    """Headless facts about the install (unit-testable, no curses)."""
    lines = [
        "GameBored OS  v%s" % __version__,
        "",
        "Games on board: %d" % len(GAMES),
        "Game list: " + ", ".join(mod.TITLE for mod in GAMES),
        "",
        "Data home: %s" % storage_mod.app_dir(),
        "Storage used: %s" % _human_bytes(storage_mod.data_size_bytes()),
        "",
        "Python: %s" % sys.version.split()[0],
        "Terminal: %s" % _terminal_name(),
    ]
    return [ln[: max(10, width - 4)] for ln in lines]


def _human_bytes(count):
    try:
        count = int(count)
    except (TypeError, ValueError):
        return "unknown"
    if count < 1024:
        return "%d bytes" % count
    if count < 1024 * 1024:
        return "%.1f KiB" % (count / 1024.0)
    return "%.1f MiB" % (count / (1024.0 * 1024.0))


def _terminal_name():
    import os
    return os.environ.get("TERM", "unknown")


def play(stdscr, _score_store=None):
    try:
        curses.curs_set(0)
    except curses.error:
        pass
    try:
        stdscr.keypad(True)
        stdscr.timeout(-1)
    except curses.error:
        pass
    while True:
        if ui.too_small(stdscr, 12, 50):
            ui.show_too_small(stdscr)
            try:
                key = stdscr.getch()
            except curses.error:
                key = -1
            if key in ui.QUIT_KEYS:
                return
            continue
        try:
            stdscr.clear()
            h, w = stdscr.getmaxyx()
            ui.header(stdscr, "ABOUT THIS SYSTEM",
                      "GameBored OS in numbers")
            for i, line in enumerate(info_lines(w)):
                y = 3 + i
                if y >= h - 2:
                    break
                attr = ui.color(1) | curses.A_BOLD if i == 0 else ui.color(7)
                ui.safe_addstr(stdscr, y, 3, line, attr)
            try:
                mono = not ui.has_color()
                extra = "colors: %s  size: %dx%d" % (
                    "mono" if mono else "yes", w, h)
                ui.centered(stdscr, h - 3, extra, ui.color(7))
            except curses.error:
                pass
            ui.footer(stdscr, "q/Esc back to the desktop | time: %s" % (
                time.strftime("%H:%M:%S")))
            stdscr.refresh()
        except curses.error:
            pass
        try:
            key = stdscr.getch()
        except curses.error:
            key = -1
        if key in ui.QUIT_KEYS or key in (10, 13, 32, curses.KEY_ENTER):
            return
        if key == curses.KEY_RESIZE:
            continue
