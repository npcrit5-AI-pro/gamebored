"""GameBored OS: a tiny desktop for the terminal arcade.

The menu is now a little operating system: a top bar (GameBored OS, live
clock, BP total), a grid of app icons you drive with the arrow keys
(Enter opens), groups for games/tools/talk/system, a boot splash, a search
launcher ('/'), and a bottom status bar with key hints. Narrow terminals
fall back to a list layout; tiny or monochrome terminals keep working.

16 games (grouped ACTION / PUZZLE / CLASSIC) plus Bored Wondering, High
Scores, the Score Translator, and Help live on the desktop next to the
new apps: Notes, Calculator, Clock, Calendar, To-do, Eliza, Parry,
Animals, Eliza vs Parry, Settings, About.
"""

import curses
import os
import time
import traceback

from . import animals as animals_mod
from . import calendarapp as calendar_mod
from . import calc as calc_mod
from . import clockapp as clock_mod
from . import eliza as eliza_mod
from . import extras as extras_mod
from . import notes as notes_mod
from . import parry as parry_mod
from . import scores as scores_mod
from . import settings as settings_mod
from . import sysinfo as sysinfo_mod
from . import todo as todo_mod
from . import translator as translator_mod
from . import ui
from . import versus as versus_mod
from . import wondering as wondering_mod
from . import __version__ as _pkg_version
from .games import GAMES

LOGO = [
    "  ____                         ___                         _ ",
    " / ___| __ _ _ __ ___   ___   | _ )  ___  _ _ ___  ___  __| |",
    " \\____|\\__,_|_| |_| |_|\\___|  |___/ \\___/|_| \\___|\\___|\\__,_|",
]

SUBTITLE = "Bored? Game on! Pick a game or app: (v%s)" % _pkg_version

GAME_HOTKEYS = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0",
                "a", "b", "c", "d", "e", "f"]

EXTRA_ENTRIES = [
    {"hotkey": "W", "title": "Bored Wondering", "desc": "Search the web, keyless",
     "kind": "wondering"},
    {"hotkey": "H", "title": "High Scores", "desc": "Every best in raw + Bored Points",
     "kind": "scores"},
    {"hotkey": "T", "title": "Score Translator", "desc": "Raw number -> BP for any game",
     "kind": "translator"},
    {"hotkey": "?", "title": "Help", "desc": "How to play everything",
     "kind": "help"},
]

TOOL_ENTRIES = [
    {"hotkey": "N", "title": "Notes", "desc": "Jot it down, keep it",
     "kind": "app", "run": notes_mod.play, "game_id": "notes"},
    {"hotkey": "R", "title": "Calculator", "desc": "Quick safe arithmetic",
     "kind": "app", "run": calc_mod.play, "game_id": "calc"},
    {"hotkey": "L", "title": "Clock", "desc": "Time, stopwatch, timer",
     "kind": "app", "run": clock_mod.play, "game_id": "clock"},
    {"hotkey": "Y", "title": "Calendar", "desc": "Month at a glance",
     "kind": "app", "run": calendar_mod.play, "game_id": "calendar"},
    {"hotkey": "O", "title": "To-do", "desc": "Stuff to get done",
     "kind": "app", "run": todo_mod.play, "game_id": "todo"},
]

SYSTEM_ENTRIES = [
    {"hotkey": "S", "title": "Settings", "desc": "Make it yours",
     "kind": "app", "run": settings_mod.play, "game_id": "settings"},
    {"hotkey": "I", "title": "About", "desc": "This machine, in numbers",
     "kind": "app", "run": sysinfo_mod.play, "game_id": "about"},
]

TALK_ENTRIES = [
    {"hotkey": "J", "title": "Eliza", "desc": "A caring (mechanical) listener",
     "kind": "app", "run": eliza_mod.play, "game_id": "eliza"},
    {"hotkey": "K", "title": "Parry", "desc": "A troubled soul (1972 classic)",
     "kind": "app", "run": parry_mod.play, "game_id": "parry"},
    {"hotkey": "U", "title": "Animals", "desc": "Think of an animal, I guess it",
     "kind": "app", "run": animals_mod.play, "game_id": "animals"},
    {"hotkey": "V", "title": "Eliza vs Parry", "desc": "1972 ARPANET rematch, live",
     "kind": "app", "run": versus_mod.play, "game_id": "versus"},
]

TILE_W = 19
TILE_H = 4
GRID_MIN_W = 70
DESKTOP_MIN_H = 14
DESKTOP_MIN_W = 50


def build_entries():
    """Flat entries: 16 games, then Explore, Tools, Talk, System apps.

    Game hotkeys stay registry-based (1-9,0,a-f in GAMES order) so every
    game keeps a stable key; apps add unique letter hotkeys.
    """
    games = []
    for i, mod in enumerate(GAMES):
        hotkey = GAME_HOTKEYS[i] if i < len(GAME_HOTKEYS) else ""
        games.append({
            "kind": "game", "category": getattr(mod, "CATEGORY", "MORE"),
            "hotkey": hotkey, "title": mod.TITLE, "desc": mod.DESCRIPTION,
            "controls": mod.CONTROLS, "mod": mod, "order": i,
        })
    order = {"ACTION": 0, "PUZZLE": 1, "CLASSIC": 2, "MORE": 3}
    games.sort(key=lambda e: (order.get(e["category"], 9), e["order"]))
    entries = games
    for extra in EXTRA_ENTRIES:
        entries.append(dict(extra, category="EXPLORE",
                            controls=_extra_controls(extra["kind"])))
    for tool in TOOL_ENTRIES:
        entries.append(dict(tool, category="TOOLS",
                            controls=getattr(tool["run"], "__doc__", "")
                            or tool["desc"]))
    for talk in TALK_ENTRIES:
        entries.append(dict(talk, category="TALK",
                            controls=getattr(talk["run"], "__doc__", "")
                            or talk["desc"]))
    for system in SYSTEM_ENTRIES:
        entries.append(dict(system, category="SYSTEM",
                            controls="Settings and system info | q back"))
    return entries


def _extra_controls(kind):
    if kind == "wondering":
        return wondering_mod.CONTROLS
    if kind == "scores":
        return "Up/Down scroll | q/Esc menu"
    if kind == "translator":
        return "Pick a game, type a number | q back"
    return "Any key back to menu"


def _commas(n):
    s = "%d" % int(n)
    out = ""
    while len(s) > 3:
        out = "," + s[-3:] + out
        s = s[:-3]
    return s + out


def _apply_filter(entries, query):
    """Entries matching the filter query (title/desc/hotkey/category)."""
    q = (query or "").strip().lower()
    if not q:
        return list(entries or [])
    out = []
    for entry in entries or []:
        try:
            hay = "%s %s %s %s" % (entry.get("title", ""),
                                   entry.get("desc", ""),
                                   entry.get("hotkey", ""),
                                   entry.get("category", ""))
        except Exception:
            continue
        if q in hay.lower():
            out.append(entry)
    return out


def grid_cols(width, tile_w=TILE_W):
    """How many icon tiles fit across. Headless-testable."""
    try:
        return max(1, int(width) // max(8, int(tile_w)))
    except (TypeError, ValueError):
        return 1


def move_selection(sel, count, cols, key):
    """Arrow-key movement over a linear index laid out in `cols` columns."""
    if not count:
        return 0
    sel = sel % count
    if key in ("left",):
        return (sel - 1) % count
    if key in ("right",):
        return (sel + 1) % count
    if key in ("up",):
        return (sel - cols) % count
    if key in ("down",):
        return (sel + cols) % count
    return sel


def desktop_too_small(win):
    """True when even the fallback desktop cannot fit (tiny terminal)."""
    try:
        h, w = win.getmaxyx()
        return h < DESKTOP_MIN_H or w < DESKTOP_MIN_W
    except curses.error:
        return True


def _draw_topbar(win, score_store):
    try:
        h, w = win.getmaxyx()
    except curses.error:
        return
    total = translator_mod.total_bp(score_store)
    clock = time.strftime("%H:%M")
    left = " GameBored OS"
    right = "%s BP  %s " % (_commas(total), clock)
    ui.safe_addstr(win, 0, 0, " " * w, curses.A_REVERSE)
    ui.safe_addstr(win, 0, 0, left[: w - 1], curses.A_REVERSE | curses.A_BOLD)
    ui.safe_addstr(win, 0, max(0, w - len(right) - 1), right[: w - 1],
                   curses.A_REVERSE | curses.A_BOLD)


def _layout_grid(entries, cols):
    """Rows of ('header', category) / ('tile', entry_idx) for the grid."""
    rows, current = [], []
    last_cat = None
    for idx, entry in enumerate(entries):
        if entry.get("category") != last_cat:
            if current:
                rows.append(current)
                current = []
            last_cat = entry.get("category")
            rows.append(("header", last_cat))
        current.append(("tile", idx))
        if len(current) >= cols:
            rows.append(current)
            current = []
    if current:
        rows.append(current)
    return rows


def _draw_tile(win, y, x, entry, selected):
    w = TILE_W - 1
    label = "[%s]" % entry.get("hotkey", "?")
    name = str(entry.get("title", "?"))[: w - 2]
    attr = ui.color(3) | curses.A_BOLD
    if entry.get("kind") == "game":
        try:
            attr = ui.color((GAMES.index(entry["mod"]) % 6) + 1)
        except (ValueError, KeyError):
            attr = ui.color(7)
    if selected:
        attr = curses.A_REVERSE | curses.A_BOLD
    ui.safe_addstr(win, y, x, "+" + "-" * (w - 2) + "+", attr)
    ui.safe_addstr(win, y + 1, x, "|" + label[: w - 2].ljust(w - 2) + "|",
                   attr)
    ui.safe_addstr(win, y + 2, x, "|" + name.ljust(w - 2) + "|", attr)
    ui.safe_addstr(win, y + 3, x, "+" + "-" * (w - 2) + "+", attr)


def _draw_desktop(win, selected, score_store, shown, status=None):
    h, w = win.getmaxyx()
    _draw_topbar(win, score_store)
    ui.centered(win, 1, SUBTITLE, ui.color(3) | curses.A_BOLD)
    top = 2
    footer_rows = 3
    avail = max(1, h - top - footer_rows)
    cols = grid_cols(w)
    rows = _layout_grid(shown, cols)

    def _row_h(row):
        return 1 if isinstance(row, tuple) else TILE_H

    # find the visual row holding the selection
    sel_row = 0
    for i, row in enumerate(rows):
        if isinstance(row, list) and any(
                kind == "tile" and idx == selected % len(shown)
                for kind, idx in row):
            sel_row = i
            break
    # scroll so the selected row fits on screen
    start = 0
    while (start < sel_row and
           sum(_row_h(r) for r in rows[start:sel_row + 1]) > avail):
        start += 1
    row_y = top
    for row in rows[start:]:
        need = _row_h(row)
        if row_y + need > top + avail:
            break
        if isinstance(row, tuple):
            ui.safe_addstr(win, row_y, max(2, (w - 60) // 2),
                           "- %s -" % row[1], ui.color(6) | curses.A_BOLD)
            row_y += 1
            continue
        for col, (kind, idx) in enumerate(row):
            x = max(0, (w - cols * TILE_W) // 2) + col * TILE_W
            _draw_tile(win, row_y, x, shown[idx],
                       idx == selected % len(shown))
        row_y += TILE_H
    if start > 0 and top < h - footer_rows:
        ui.safe_addstr(win, top, max(0, w // 2 - 6), "...more...",
                       ui.color(7))
    if h - 3 >= 0:
        total = translator_mod.total_bp(score_store)
        ui.centered(win, h - 3, "Combined total: %s BP across %d games" % (
            _commas(total), len(GAMES)), ui.color(2) | curses.A_BOLD)
    if h - 2 >= 0 and shown:
        entry = shown[selected % len(shown)]
        detail = "%s: %s" % (entry["title"], entry["controls"])
        ui.centered(win, h - 2, detail[: w - 2], ui.color(7))
    if status and h - 2 >= 0:
        ui.centered(win, h - 2, status[: w - 2],
                    ui.color(3) | curses.A_BOLD)
    ui.footer(win, "Arrows move | Enter open | 1-9,0,a-f games | "
                   "N notes R calc L clock Y cal O todo J eliza K parry | "
                   "U animals V vs S setup I about | "
                   "W search H scores T translator ? help | / filter | q quit")


def _draw_list(win, selected, score_store, shown, status=None):
    """Narrow-terminal fallback: the classic one-entry-per-row list."""
    h, w = win.getmaxyx()
    _draw_topbar(win, score_store)
    ui.centered(win, 1, SUBTITLE, ui.color(3) | curses.A_BOLD)
    top = 2
    footer_rows = 3
    visible = max(1, h - top - footer_rows)
    lines = []
    last_cat = None
    for idx, entry in enumerate(shown):
        if entry["category"] != last_cat:
            last_cat = entry["category"]
            lines.append(("header", last_cat))
        lines.append(("entry", idx))
    sel_line = next((i for i, ln in enumerate(lines)
                     if ln[0] == "entry" and ln[1] == selected % len(shown)),
                    0)
    start = max(0, min(sel_line - visible // 2, len(lines) - visible))
    end = min(len(lines), start + visible)
    start = max(0, end - visible)
    row = top
    for ln in lines[start:end]:
        if row >= h - footer_rows:
            break
        if ln[0] == "header":
            ui.safe_addstr(win, row, max(2, (w - 60) // 2),
                           "- %s -" % ln[1], ui.color(6) | curses.A_BOLD)
            row += 1
            continue
        idx = ln[1]
        entry = shown[idx]
        if entry["kind"] in ("game",):
            mod = entry["mod"]
            best = scores_mod.get_entry(score_store, mod.GAME_ID)["high"]
            bp = translator_mod.to_bp(mod.GAME_ID, best)
            label = " %s  %-12s  %-22s  %5d %s BP" % (
                entry["hotkey"], entry["title"][:12], entry["desc"][:22],
                best, _commas(bp))
        else:
            label = " %s  %-17s  %-28s" % (
                entry["hotkey"], entry["title"][:17], entry["desc"][:28])
        label = label[: max(0, w - 4)]
        x = max(0, (w - len(label)) // 2)
        if idx == selected % len(shown):
            attr = curses.A_REVERSE | curses.A_BOLD
        elif entry["kind"] == "game":
            attr = ui.color((GAMES.index(entry["mod"]) % 6) + 1)
        else:
            attr = ui.color(3) | curses.A_BOLD
        ui.safe_addstr(win, row, x, label, attr)
        row += 1
    if start > 0 and top < h - footer_rows:
        ui.safe_addstr(win, top, max(0, w // 2 - 6), "...more...",
                       ui.color(7))
    if h - 3 >= 0:
        total = translator_mod.total_bp(score_store)
        ui.centered(win, h - 3, "Combined total: %s BP across %d games" % (
            _commas(total), len(GAMES)), ui.color(2) | curses.A_BOLD)
    if h - 2 >= 0 and shown:
        entry = shown[selected % len(shown)]
        detail = "%s: %s" % (entry["title"], entry["controls"])
        ui.centered(win, h - 2, detail[: w - 2], ui.color(7))
    if status and h - 2 >= 0:
        ui.centered(win, h - 2, status[: w - 2],
                    ui.color(3) | curses.A_BOLD)
    ui.footer(win, "Up/Down+j/k move | Enter open | hotkeys | "
                   "/ filter | q quit")


def draw_menu(win, selected, score_store, entries=None, status=None):
    if entries is None:
        entries = build_entries()
    if not entries:
        try:
            win.clear()
            h, w = win.getmaxyx()
            ui.centered(win, 0, "GAMEBORED", ui.color(1) | curses.A_BOLD)
            ui.centered(win, 2, "No entries to show.", ui.color(7))
            if status:
                ui.centered(win, h - 2, status[: w - 2],
                            ui.color(3) | curses.A_BOLD)
            ui.footer(win, "q quit")
            win.refresh()
        except curses.error:
            pass
        return
    try:
        win.clear()
    except curses.error:
        pass
    try:
        _, w = win.getmaxyx()
    except curses.error:
        return
    try:
        if w >= GRID_MIN_W:
            _draw_desktop(win, selected, score_store, entries, status=status)
        else:
            _draw_list(win, selected, score_store, entries, status=status)
        win.refresh()
    except curses.error:
        pass


def hotkey_index(entries, key):
    """Map a pressed key to an entry index, or None."""
    if not isinstance(key, int):
        return None
    if 0 <= key <= 255:
        ch = chr(key)
        for i, e in enumerate(entries):
            if e.get("hotkey") and e["hotkey"].lower() == ch.lower():
                return i
    return None


LAST_KEY = "_menu_last"


def _entry_id(entry):
    """Stable id for a menu entry: game/app id, or kind:title for extras."""
    try:
        if entry.get("kind") in ("game", "app"):
            mod = entry.get("mod")
            gid = getattr(mod, "GAME_ID", None) if mod is not None else None
            gid = gid or entry.get("game_id") or entry.get("title")
            return "game:%s" % gid
        return "%s:%s" % (entry.get("kind"), entry.get("title"))
    except Exception:
        return ""


def _restore_selected(score_store, entries):
    """Index of the entry picked last time, or 0 when unknown."""
    want = None
    try:
        if isinstance(score_store, dict):
            want = score_store.get(LAST_KEY)
    except Exception:
        want = None
    if not isinstance(want, str) or not want:
        return 0
    for i, entry in enumerate(entries or []):
        if _entry_id(entry) == want:
            return i
    return 0


def _remember_selected(score_store, entries, idx):
    """Persist the picked entry id; never breaks saving."""
    if not isinstance(score_store, dict) or not entries:
        return
    try:
        score_store[LAST_KEY] = _entry_id(entries[idx % len(entries)])
        scores_mod.save(score_store)
    except Exception:
        pass


def _boot_splash(stdscr, settings):
    """Short skippable splash. Honors Settings + GAMEBORED_NO_SPLASH."""
    import sys

    try:
        if not sys.stdout.isatty():
            return  # headless tests / pipes: go straight to the desktop
    except Exception:
        pass
    try:
        if os.environ.get("GAMEBORED_NO_SPLASH", "").strip() not in (
                "", "0", "no", "false", "off"):
            return
    except Exception:
        pass
    try:
        if settings is not None and not settings_mod.get(settings,
                                                          "boot_splash"):
            return
    except Exception:
        pass
    try:
        stdscr.timeout(150)
    except curses.error:
        pass
    frames = 6
    for frame in range(frames):
        try:
            stdscr.clear()
            h, w = stdscr.getmaxyx()
            y = max(0, h // 2 - 4)
            for line in LOGO:
                ui.centered(stdscr, y, line[: w - 2],
                            ui.color(1) | curses.A_BOLD)
                y += 1
            ui.centered(stdscr, y + 1, "GameBored OS  v%s" % _pkg_version,
                        ui.color(3) | curses.A_BOLD)
            bar = "[" + "=" * frame + " " * (frames - 1 - frame) + "]"
            ui.centered(stdscr, y + 3, "Loading your desktop  %s" % bar,
                        ui.color(7))
            ui.footer(stdscr, "any key skips the splash")
            stdscr.refresh()
        except curses.error:
            pass
        try:
            key = stdscr.getch()
        except curses.error:
            key = -1
        if key != -1 and key != curses.KEY_RESIZE:
            break
    try:
        stdscr.timeout(-1)
    except curses.error:
        pass


def menu_loop(stdscr):
    try:
        curses.curs_set(0)
    except curses.error:
        pass
    try:
        stdscr.keypad(True)
    except curses.error:
        pass
    ui.init_colors()
    settings = settings_mod.load()
    ui.apply_theme(settings_mod.get(settings, "theme"))
    try:
        stdscr.timeout(-1)
    except curses.error:
        pass
    _boot_splash(stdscr, settings)
    try:
        stdscr.timeout(500)
    except curses.error:
        pass
    score_store = scores_mod.load()
    entries = build_entries()
    if not entries:
        try:
            stdscr.clear()
        except curses.error:
            pass
        ui.centered(stdscr, 0, "GAMEBORED", ui.color(1) | curses.A_BOLD)
        ui.centered(stdscr, 2, "No entries to show.", ui.color(7))
        ui.footer(stdscr, "q quit")
        try:
            stdscr.refresh()
            stdscr.timeout(-1)
            stdscr.getch()
        except curses.error:
            pass
        return
    selected = _restore_selected(score_store, entries)
    filtering, query = False, ""
    while True:
        if desktop_too_small(stdscr):
            ui.show_too_small(stdscr)
            try:
                key = stdscr.getch()
            except curses.error:
                key = -1
            if key in ui.QUIT_KEYS:
                return
            elif key == curses.KEY_RESIZE:
                continue
            continue
        shown = _apply_filter(entries, query) if filtering else entries
        if shown:
            selected = selected % len(shown)
        status = None
        if filtering:
            status = "Filter: %s_ (%d match%s) | Enter open | Esc clear" % (
                query, len(shown), "" if len(shown) == 1 else "es")
        try:
            _, w = stdscr.getmaxyx()
            cols = grid_cols(w)
        except curses.error:
            cols = 1
        draw_menu(stdscr, selected, score_store, shown, status=status)
        try:
            key = stdscr.getch()
        except curses.error:
            key = -1
        if key == -1:
            # clock tick redraw; reload theme-able bits cheaply
            score_store = scores_mod.load()
            entries = build_entries()
            continue
        if key in ui.QUIT_KEYS:
            if filtering:
                filtering, query = False, ""
                selected = _restore_selected(score_store, entries)
                continue
            return
        if filtering:
            if key == curses.KEY_RESIZE:
                continue
            elif key in (10, 13, curses.KEY_ENTER):
                if shown:
                    target = shown[selected % len(shown)]
                    idx = entries.index(target)
                    _remember_selected(score_store, entries, idx)
                    launch_entry(stdscr, target, score_store)
                    _hide_cursor(stdscr)
                    score_store = scores_mod.load()
                    entries = build_entries()
                filtering, query = False, ""
                selected = _restore_selected(score_store, entries)
            elif key == curses.KEY_UP:
                if shown:
                    selected = move_selection(selected, len(shown), cols,
                                              "up")
            elif key == curses.KEY_DOWN:
                if shown:
                    selected = move_selection(selected, len(shown), cols,
                                              "down")
            elif key == curses.KEY_LEFT:
                if shown:
                    selected = move_selection(selected, len(shown), cols,
                                              "left")
            elif key == curses.KEY_RIGHT:
                if shown:
                    selected = move_selection(selected, len(shown), cols,
                                              "right")
            elif key in (curses.KEY_BACKSPACE, 127, 8):
                query = query[:-1]
                selected = 0
            elif 32 <= key <= 126 and len(query) < 24:
                query += chr(key)
                selected = 0
            continue
        if key == ord("/"):
            filtering, query = True, ""
            selected = 0
            continue
        elif key == curses.KEY_UP or key == ord("k"):
            selected = move_selection(selected, len(entries), cols, "up")
        elif key == curses.KEY_DOWN or key == ord("j"):
            selected = move_selection(selected, len(entries), cols, "down")
        elif key == curses.KEY_LEFT:
            selected = move_selection(selected, len(entries), cols, "left")
        elif key == curses.KEY_RIGHT:
            selected = move_selection(selected, len(entries), cols, "right")
        elif key in (10, 13, curses.KEY_ENTER, ord(" ")):
            _remember_selected(score_store, entries, selected)
            launch_entry(stdscr, entries[selected], score_store)
            _hide_cursor(stdscr)
            score_store = scores_mod.load()
        elif key == curses.KEY_RESIZE:
            continue
        else:
            idx = hotkey_index(entries, key)
            if idx is not None:
                selected = idx
                _remember_selected(score_store, entries, selected)
                launch_entry(stdscr, entries[idx], score_store)
                _hide_cursor(stdscr)
                score_store = scores_mod.load()


def _hide_cursor(stdscr):
    """Games with text entry show the cursor; always hide it for the menu."""
    try:
        curses.curs_set(0)
    except curses.error:
        pass
    try:
        stdscr.keypad(True)
        stdscr.timeout(500)
    except curses.error:
        pass


def launch_entry(stdscr, entry, score_store):
    kind = entry.get("kind")
    try:
        if kind == "game":
            launch(stdscr, entry["mod"], score_store)
        elif kind == "app":
            entry["run"](stdscr, score_store)
            settings = settings_mod.load()
            ui.apply_theme(settings_mod.get(settings, "theme"))
        elif kind == "wondering":
            wondering_mod.play(stdscr, score_store)
            _hide_cursor(stdscr)
        elif kind == "scores":
            extras_mod.show_high_scores(stdscr, score_store)
        elif kind == "translator":
            extras_mod.show_translator(stdscr)
        elif kind == "help":
            extras_mod.show_help(stdscr, GAMES)
    except Exception:
        try:
            stdscr.clear()
            h, w = stdscr.getmaxyx()
            ui.centered(stdscr, h // 2 - 1, "Oops, %s crashed!" % entry.get("title", "?"),
                        ui.color(5) | curses.A_BOLD)
            ui.centered(stdscr, h // 2, "Press any key for the menu",
                        ui.color(7))
            try:
                detail = traceback.format_exc(limit=3).strip().splitlines()
                if detail:
                    ui.centered(stdscr, h // 2 + 2, detail[-1][: w - 2],
                                ui.color(7))
            except curses.error:
                pass
            stdscr.refresh()
            stdscr.timeout(-1)
            stdscr.getch()
        except curses.error:
            pass


def launch(stdscr, mod, score_store):
    try:
        mod.play(stdscr, score_store)
    except Exception:
        # Never trap the user in a broken game: show the error, then menu.
        try:
            stdscr.clear()
            h, w = stdscr.getmaxyx()
            ui.centered(stdscr, h // 2 - 1, "Oops, %s crashed!" % mod.TITLE,
                        ui.color(5) | curses.A_BOLD)
            ui.centered(stdscr, h // 2, "Press any key for the menu",
                        ui.color(7))
            try:
                detail = traceback.format_exc(limit=3).strip().splitlines()
                if detail:
                    ui.centered(stdscr, h // 2 + 2, detail[-1][: w - 2],
                                ui.color(7))
            except curses.error:
                pass
            stdscr.refresh()
            stdscr.timeout(-1)
            stdscr.getch()
        except curses.error:
            pass


def main(stdscr):
    menu_loop(ui.InputWindow(stdscr))


def run():
    """Entry point: always restore the terminal, even on crash/resize."""
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        pass
    finally:
        # Belt and suspenders: make sure the cooked terminal comes back.
        try:
            curses.endwin()
        except Exception:
            pass
