"""Human-like CPU opponents: thinking pauses with a live indicator.

Every game with a computer opponent calls think() before the CPU moves so
the computer feels like a person (short randomized pause, animated dots)
instead of answering instantly. The UI stays responsive: q/Esc during the
pause backs out immediately.

Honor the Settings app (cpu_think on/off, cpu_speed) and the
GAMEBORED_NO_CPU_DELAY environment variable (set it to "1" in tests so
the suite stays fast). Only the standard library is used.
"""

import curses
import os
import random
import time

from . import settings as settings_mod
from . import ui

ENV_VAR = "GAMEBORED_NO_CPU_DELAY"

MIN_DELAY = 0.4
MAX_DELAY = 1.5
HARD_EXTRA = 0.6


def env_disabled():
    """True when the test env var disables all CPU delays."""
    try:
        return os.environ.get(ENV_VAR, "").strip() not in ("", "0", "no",
                                                           "false", "off")
    except Exception:
        return False


def settings_disabled(settings):
    """True when the player turned the CPU think pause off in Settings."""
    try:
        if settings is None:
            return False
        return not settings_mod.get(settings, "cpu_think")
    except Exception:
        return False


def speed_multiplier(settings):
    """Delay multiplier from Settings (0.5 relaxed / 1.0 normal / 2.0 brisk).

    Brisk means a *shorter* pause, so higher values divide the delay.
    """
    try:
        if settings is None:
            return 1.0
        speed = float(settings_mod.get(settings, "cpu_speed"))
        if speed <= 0:
            return 1.0
        return 1.0 / speed
    except (TypeError, ValueError):
        return 1.0


def delay_seconds(difficulty=0.0, settings=None, rng=None):
    """How long the CPU should 'think', in seconds (0 when disabled).

    difficulty 0.0 = routine move, 1.0 = hard position (adds up to
    HARD_EXTRA seconds). Callers pass harder positions a higher value.
    """
    if env_disabled() or settings_disabled(settings):
        return 0.0
    try:
        difficulty = max(0.0, min(1.0, float(difficulty)))
    except (TypeError, ValueError):
        difficulty = 0.0
    roll = (rng or random).uniform(MIN_DELAY, MAX_DELAY)
    total = (roll + difficulty * HARD_EXTRA) * speed_multiplier(settings)
    return max(0.0, total)


def think(win, seconds=None, difficulty=0.0, settings=None, label=None):
    """Pause with a 'CPU is thinking...' indicator. Returns 'done'/'quit'.

    Draws animated dots while pumping the input queue so the screen never
    freezes: q/Esc aborts the pause at once. When the delay is disabled
    this returns 'done' without blocking and without swallowing input.
    """
    if seconds is None:
        seconds = delay_seconds(difficulty=difficulty, settings=settings)
    try:
        seconds = max(0.0, float(seconds))
    except (TypeError, ValueError):
        seconds = 0.0
    if seconds <= 0.0:
        # Fast path for tests / disabled pauses: poll once so a pending
        # q/Esc is still honored, but push anything else back.
        try:
            win.timeout(0)
        except curses.error:
            pass
        try:
            key = win.getch()
        except curses.error:
            key = -1
        finally:
            try:
                win.timeout(-1)
            except curses.error:
                pass
        if key in ui.QUIT_KEYS:
            return "quit"
        if key not in (-1, curses.KEY_RESIZE):
            try:
                curses.ungetch(key)
            except curses.error:
                pass
        return "done"
    label = label or "CPU is thinking"
    deadline = time.time() + seconds
    try:
        win.timeout(120)
    except curses.error:
        pass
    dots = 0
    while True:
        dots = (dots + 1) % 4
        try:
            h, _w = win.getmaxyx()
            ui.centered(win, h - 4 if h > 6 else max(0, h - 1),
                        "%s%s" % (label, "." * dots),
                        ui.color(3) | curses.A_BOLD)
            win.refresh()
        except curses.error:
            pass
        try:
            key = win.getch()
        except curses.error:
            key = -1
        if key in ui.QUIT_KEYS:
            try:
                win.timeout(-1)
            except curses.error:
                pass
            return "quit"
        if key == curses.KEY_RESIZE:
            continue
        if time.time() >= deadline:
            break
    try:
        win.timeout(-1)
    except curses.error:
        pass
    return "done"
