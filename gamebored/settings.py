"""GameBored settings: theme, CPU think delay, boot splash.

Stored as JSON in the data dir so choices survive upgrades. Only the
standard library is used.
"""

import os

from . import storage as storage_mod

FILE_NAME = "settings.json"

THEMES = ("default", "midnight", "forest", "mono")
CPU_SPEEDS = (0.5, 1.0, 2.0)
CPU_SPEED_LABELS = {0.5: "relaxed", 1.0: "normal", 2.0: "brisk"}

DEFAULTS = {
    "theme": "default",
    "cpu_think": True,
    "cpu_speed": 1.0,
    "boot_splash": True,
}


def _clean(raw):
    """Validate a raw dict into a full settings dict. Never raises."""
    out = dict(DEFAULTS)
    if not isinstance(raw, dict):
        return out
    theme = raw.get("theme")
    if isinstance(theme, str) and theme in THEMES:
        out["theme"] = theme
    think = raw.get("cpu_think")
    if isinstance(think, bool):
        out["cpu_think"] = think
    elif isinstance(think, int) and not isinstance(think, bool):
        out["cpu_think"] = bool(think)
    speed = raw.get("cpu_speed")
    try:
        speed = float(speed)
    except (TypeError, ValueError):
        speed = 1.0
    if speed in CPU_SPEEDS:
        out["cpu_speed"] = speed
    splash = raw.get("boot_splash")
    if isinstance(splash, bool):
        out["boot_splash"] = splash
    return out


def load(path=None):
    raw = storage_mod.load_json(FILE_NAME, dict(DEFAULTS),
                                path=path or storage_mod.data_path(FILE_NAME))
    return _clean(raw)


def save(settings, path=None):
    storage_mod.save_json(FILE_NAME, _clean(settings),
                          path=path or storage_mod.data_path(FILE_NAME))


def get(settings, key):
    if isinstance(settings, dict) and key in DEFAULTS:
        try:
            return _clean(settings)[key]
        except Exception:
            pass
    return DEFAULTS.get(key)


def set(settings, key, value, path=None):
    """Return a new validated settings dict with key updated (and saved)."""
    current = _clean(settings)
    if key not in DEFAULTS:
        return current
    current[key] = value
    cleaned = _clean(current)
    try:
        save(cleaned, path=path)
    except Exception:
        pass
    return cleaned


def theme_pairs(theme):
    """Color-pair overrides for a theme: {pair: (fg, bg curses consts)}.

    Returned as color *names* so ui can resolve them (keeps curses
    constants out of the settings layer, which stays headless-testable).
    """
    if theme == "mono":
        return {}
    if theme == "midnight":
        return {1: ("MAGENTA", None), 2: ("CYAN", None),
                3: ("WHITE", None)}
    if theme == "forest":
        return {1: ("GREEN", None), 2: ("YELLOW", None),
                5: ("GREEN", None)}
    return {}


def data_file():
    return os.path.join(storage_mod.app_dir(), FILE_NAME)


TITLE = "Settings"
DESCRIPTION = "Make it yours"
CONTROLS = "Up/Down pick | Left/Right change | q menu"
CATEGORY = "System"

_ROWS = ("theme", "cpu_think", "cpu_speed", "boot_splash")
_LABELS = {
    "theme": "Color theme",
    "cpu_think": "CPU think pause",
    "cpu_speed": "CPU think speed",
    "boot_splash": "Boot splash",
}


def _row_value(key, settings):
    if key == "theme":
        return get(settings, "theme")
    if key == "cpu_think":
        return "on" if get(settings, "cpu_think") else "off"
    if key == "cpu_speed":
        speed = get(settings, "cpu_speed")
        return "%s (%.1fx)" % (CPU_SPEED_LABELS.get(speed, "normal"), speed)
    if key == "boot_splash":
        return "on" if get(settings, "boot_splash") else "off"
    return ""


def _cycle(key, settings, direction):
    if key == "theme":
        choices = list(THEMES)
        cur = choices.index(get(settings, "theme"))
        return set(settings, "theme",
                   choices[(cur + direction) % len(choices)])
    if key == "cpu_think":
        return set(settings, "cpu_think", not get(settings, "cpu_think"))
    if key == "cpu_speed":
        choices = list(CPU_SPEEDS)
        cur = choices.index(get(settings, "cpu_speed"))
        return set(settings, "cpu_speed",
                   choices[(cur + direction) % len(choices)])
    if key == "boot_splash":
        return set(settings, "boot_splash",
                   not get(settings, "boot_splash"))
    return settings


def play(stdscr, _score_store=None):
    import curses

    from . import ui as ui_mod

    try:
        curses.curs_set(0)
    except curses.error:
        pass
    try:
        stdscr.keypad(True)
        stdscr.timeout(-1)
    except curses.error:
        pass
    current = load()
    sel = 0
    while True:
        if ui_mod.too_small(stdscr, 12, 50):
            ui_mod.show_too_small(stdscr)
            try:
                key = stdscr.getch()
            except curses.error:
                key = -1
            if key in ui_mod.QUIT_KEYS:
                return
            continue
        try:
            stdscr.clear()
            h, w = stdscr.getmaxyx()
            ui_mod.header(stdscr, "SETTINGS", "saved automatically")
            for i, key_name in enumerate(_ROWS):
                y = 3 + i * 2
                if y >= h - 3:
                    break
                line = "%-16s  < %s >" % (_LABELS[key_name],
                                         _row_value(key_name, current))
                attr = (curses.A_REVERSE | curses.A_BOLD if i == sel
                        else ui_mod.color(7))
                ui_mod.safe_addstr(stdscr, y, 4, line[: w - 8], attr)
                if i == sel:
                    hint = {"theme": "pick a color scheme",
                            "cpu_think": "pause before CPU moves",
                            "cpu_speed": "relaxed 0.5x / normal / brisk 2x",
                            "boot_splash": "logo on startup"}[key_name]
                    ui_mod.safe_addstr(stdscr, y + 1, 6, hint[: w - 10],
                                       ui_mod.color(3))
            ui_mod.game_footer(stdscr, CONTROLS)
            stdscr.refresh()
        except curses.error:
            pass
        try:
            key = stdscr.getch()
        except curses.error:
            key = -1
        if key in ui_mod.QUIT_KEYS:
            return
        if key == curses.KEY_RESIZE:
            continue
        if key in ui_mod.HELP_KEYS:
            ui_mod.show_help_overlay(stdscr, TITLE, CONTROLS)
            continue
        if key == curses.KEY_UP:
            sel = (sel - 1) % len(_ROWS)
        elif key == curses.KEY_DOWN:
            sel = (sel + 1) % len(_ROWS)
        elif key in (curses.KEY_LEFT, curses.KEY_RIGHT, 10, 13,
                     curses.KEY_ENTER, ord(" ")):
            direction = -1 if key == curses.KEY_LEFT else 1
            current = _cycle(_ROWS[sel], current, direction)
