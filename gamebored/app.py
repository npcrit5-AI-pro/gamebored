"""GameBored main menu: pick a game, play, come back, quit with q/Esc.

The menu lists 16 games (grouped by category) plus extras: Bored Wondering
(keyless web search), High Scores (every raw best translated into Bored
Points, with a combined all-games total), a Score Translator (pick a game,
type any raw number, see the BP value), and Help.
"""

import curses
import traceback

from . import extras as extras_mod
from . import scores as scores_mod
from . import translator as translator_mod
from . import ui
from . import wondering as wondering_mod
from . import __version__ as _pkg_version
from .games import GAMES

LOGO = [
    "  ____                         ___                         _ ",
    " / ___| __ _ _ __ ___   ___   | _ )  ___  _ _ ___  ___  __| |",
    " \\____|\\__,_|_| |_| |_|\\___|  |___/ \\___/|_| \\___|\\___|\\__,_|",
]

SUBTITLE = "Bored? Game on! Pick a game: (v%s)" % _pkg_version

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


def build_entries():
    """Flat menu entries: 16 games grouped by category, then W/H/T/? extras.

    Hotkeys stay registry-based (1-9,0,a-f in GAMES order) so every game
    keeps a stable key; rows are grouped ACTION / PUZZLE / CLASSIC.
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


def draw_menu(win, selected, score_store, entries=None):
    if entries is None:
        entries = build_entries()
    if not entries:
        try:
            win.clear()
            ui.centered(win, 0, "GAMEBORED", ui.color(1) | curses.A_BOLD)
            ui.centered(win, 2, "No entries to show.", ui.color(7))
            ui.footer(win, "q quit")
            win.refresh()
        except curses.error:
            pass
        return
    try:
        win.clear()
    except curses.error:
        pass
    h, w = win.getmaxyx()
    y = 0
    for line in LOGO:
        if y >= h - 1:
            break
        ui.centered(win, y, line[: w - 2], ui.color(1) | curses.A_BOLD)
        y += 1
    if y < h - 1:
        ui.centered(win, y, SUBTITLE, ui.color(3) | curses.A_BOLD)
        y += 1
    top = y
    # scrollable list region: rows top..h-4 (h-3 total, h-2 detail, h-1 keys)
    footer_rows = 3
    visible = max(1, h - top - footer_rows)
    lines = []  # ("header", cat) or ("entry", idx)
    last_cat = None
    for idx, entry in enumerate(entries):
        if entry["category"] != last_cat:
            last_cat = entry["category"]
            lines.append(("header", last_cat))
        lines.append(("entry", idx))
    sel_line = next(i for i, ln in enumerate(lines)
                    if ln[0] == "entry" and ln[1] == selected % len(entries))
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
        entry = entries[idx]
        if entry["kind"] == "game":
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
        if idx == selected % len(entries):
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
    if h - 2 >= 0 and entries:
        entry = entries[selected % len(entries)]
        detail = "%s: %s" % (entry["title"], entry["controls"])
        ui.centered(win, h - 2, detail[: w - 2], ui.color(7))
    ui.footer(win, "Up/Down+j/k move | Enter open | 1-9,0,a-f games | "
                   "W search H scores T translator ? help | q quit")
    try:
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
    """Stable id for a menu entry: the game id, or kind:title for extras."""
    try:
        if entry.get("kind") == "game":
            return "game:%s" % entry["mod"].GAME_ID
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


def menu_loop(stdscr):
    try:
        curses.curs_set(0)
    except curses.error:
        pass
    try:
        stdscr.keypad(True)
    except curses.error:
        pass
    try:
        stdscr.timeout(-1)
    except curses.error:
        pass
    ui.init_colors()
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
    while True:
        if ui.too_small(stdscr):
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
        draw_menu(stdscr, selected, score_store, entries)
        try:
            key = stdscr.getch()
        except curses.error:
            key = -1
        if key in ui.QUIT_KEYS:
            return
        elif key == curses.KEY_UP or key == ord("k"):
            selected = (selected - 1) % len(entries)
        elif key == curses.KEY_DOWN or key == ord("j"):
            selected = (selected + 1) % len(entries)
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
        stdscr.timeout(-1)
    except curses.error:
        pass


def launch_entry(stdscr, entry, score_store):
    kind = entry.get("kind")
    try:
        if kind == "game":
            launch(stdscr, entry["mod"], score_store)
        elif kind == "wondering":
            wondering_mod.play(stdscr, score_store)
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
