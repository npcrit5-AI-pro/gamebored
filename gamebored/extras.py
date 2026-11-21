"""High Scores, Score Translator, and Help screens for GameBored.

High Scores shows every raw best translated into Bored Points (BP) with a
combined all-games total; the Translator converts any raw number into BP.
"""

import curses

from . import scores as scores_mod
from . import translator as translator_mod
from . import ui
from .games import GAMES


def _commas(n):
    s = "%d" % int(n)
    out = ""
    while len(s) > 3:
        out = "," + s[-3:] + out
        s = s[:-3]
    return s + out


def show_high_scores(win, score_store):
    """High-score table: every raw best AND its BP, plus combined total."""
    top = 0
    while True:
        if ui.too_small(win):
            ui.show_too_small(win)
            try:
                key = win.getch()
            except curses.error:
                key = -1
            if key in ui.QUIT_KEYS:
                return
            continue
        try:
            win.clear()
            h, w = win.getmaxyx()
            ui.header(win, "HIGH SCORES (raw -> Bored Points)",
                      "your legend, translated")
            rows = []
            for mod in GAMES:
                entry = scores_mod.get_entry(score_store, mod.GAME_ID)
                bp = translator_mod.to_bp(mod.GAME_ID, entry["high"])
                rows.append((mod.TITLE, entry["high"], bp,
                             entry["plays"]))
            y = 3
            visible = max(1, h - y - 3)
            for i in range(visible):
                idx = top + i
                if idx >= len(rows):
                    break
                title, high, bp, plays = rows[idx]
                line = "%-12s  best %-8d -> %8s BP" % (
                    title[:12], high, _commas(bp))
                attr = ui.color(2) | curses.A_BOLD if high else ui.color(7)
                ui.safe_addstr(win, y + i, max(2, (w - 44) // 2),
                               line[: w - 4], attr)
            if top + visible < len(rows):
                ui.safe_addstr(win, h - 2, w - 14, "(more: Up/Down)",
                               ui.color(3))
            total = translator_mod.total_bp(score_store)
            ui.centered(win, h - 3, "COMBINED TOTAL: %s BP" % _commas(total),
                        ui.color(2) | curses.A_BOLD)
            ui.footer(win, "Up/Down scroll | ? help | q/Esc back to menu")
            win.refresh()
        except curses.error:
            pass
        try:
            key = win.getch()
        except curses.error:
            key = -1
        if key in ui.QUIT_KEYS:
            return
        if key == curses.KEY_UP:
            top = max(0, top - 1)
        elif key == curses.KEY_DOWN:
            try:
                h, _ = win.getmaxyx()
            except curses.error:
                h = 24
            visible = max(1, h - 3 - 3)
            top = min(top + 1, max(0, len(rows) - visible))
        elif key == curses.KEY_RESIZE:
            continue
        elif key in ui.HELP_KEYS:
            ui.show_help_overlay(win, "High Scores",
                                 "Up/Down scroll | q/Esc menu")


def _pick_translator_game(win):
    """Return a game index, or None if the user backs out."""
    sel = 0
    while True:
        if ui.too_small(win):
            ui.show_too_small(win)
            try:
                key = win.getch()
            except curses.error:
                key = -1
            if key in ui.QUIT_KEYS:
                return None
            continue
        try:
            win.clear()
            h, w = win.getmaxyx()
            ui.header(win, "SCORE TRANSLATOR: pick a game",
                      "every score speaks Bored Points")
            top = 3
            visible = max(1, h - top - 3)
            start = max(0, min(sel - visible // 2, len(GAMES) - visible))
            end = min(len(GAMES), start + visible)
            start = max(0, end - visible)
            row = top
            for i in range(start, end):
                info = translator_mod.CONVERSIONS[GAMES[i].GAME_ID]
                line = " %s  %-12s  %s" % (
                    _game_hotkey(i), GAMES[i].TITLE, info["raw"])
                line = line[: w - 4]
                x = max(0, (w - len(line)) // 2)
                attr = (curses.A_REVERSE | curses.A_BOLD if i == sel
                        else ui.color((i % 6) + 1))
                ui.safe_addstr(win, row, x, line, attr)
                row += 1
            ui.footer(win, "1-9,0,a-f or arrows+Enter pick | ? help | q back")
            win.refresh()
        except curses.error:
            pass
        try:
            key = win.getch()
        except curses.error:
            key = -1
        if key in ui.QUIT_KEYS:
            return None
        elif key == curses.KEY_UP:
            sel = (sel - 1) % len(GAMES)
        elif key == curses.KEY_DOWN:
            sel = (sel + 1) % len(GAMES)
        elif key in (10, 13, curses.KEY_ENTER, ord(" ")):
            return sel
        elif key in ui.HELP_KEYS:
            ui.show_help_overlay(win, "Score Translator",
                                 "Pick a game, type a number | q back")
        elif key == curses.KEY_RESIZE:
            continue
        else:
            idx = _hotkey_game_index(key)
            if idx is not None:
                return idx


def _game_hotkey(i):
    if i < 9:
        return str(i + 1)
    if i == 9:
        return "0"
    return chr(ord("a") + i - 10)


def _hotkey_game_index(key):
    if 0 <= key <= 255:
        ch = chr(key).lower()
        for i in range(len(GAMES)):
            if _game_hotkey(i) == ch:
                return i
    return None


def _translator_prompt(win, game_idx):
    """Prompt for a raw number and show its BP translation."""
    mod = GAMES[game_idx]
    info = translator_mod.CONVERSIONS[mod.GAME_ID]
    buf = ""
    while True:
        if ui.too_small(win):
            ui.show_too_small(win)
            try:
                key = win.getch()
            except curses.error:
                key = -1
            if key in ui.QUIT_KEYS:
                return
            continue
        try:
            win.clear()
            h, w = win.getmaxyx()
            ui.header(win, "SCORE TRANSLATOR: %s" % mod.TITLE,
                      "Bored Points for %s" % mod.TITLE)
            ui.centered(win, 3, "Rate: %s" % info["raw"], ui.color(7))
            ui.centered(win, 4, "Example: %s" % info["example"], ui.color(7))
            ui.centered(win, 6, "Type a raw score, Enter converts:",
                        ui.color(2) | curses.A_BOLD)
            ui.centered(win, 7, (buf or "_") + " raw", curses.A_BOLD)
            if buf:
                try:
                    raw = int(buf)
                except ValueError:
                    raw = 0
                ui.centered(win, 9, "%s  ->  %s BP" % (
                    _commas(raw),
                    _commas(translator_mod.to_bp(mod.GAME_ID, raw))),
                    ui.color(8) | curses.A_BOLD)
                ui.centered(win, 10, "1 %s = %s BP" % (
                    info["raw"].split("(")[0].strip() or "point",
                    translator_mod.rate_for(mod.GAME_ID)), ui.color(7))
            ui.footer(win, "digits type | Enter converts | ? help | q back")
            win.refresh()
        except curses.error:
            pass
        try:
            key = win.getch()
        except curses.error:
            key = -1
        if key in ui.QUIT_KEYS:
            return
        elif key in (10, 13, curses.KEY_ENTER):
            buf = buf or "0"
            continue
        elif key in (curses.KEY_BACKSPACE, 127, 8):
            buf = buf[:-1]
        elif key in ui.HELP_KEYS:
            ui.show_help_overlay(win, "Score Translator",
                                 "Type a raw score, Enter converts | q back")
        elif ord("0") <= key <= ord("9") and len(buf) < 9:
            buf += chr(key)


def show_translator(win):
    while True:
        idx = _pick_translator_game(win)
        if idx is None:
            return
        _translator_prompt(win, idx)


def build_help_lines(game_mods):
    lines = [
        "Welcome to GameBored! Pick a game, play, come back.",
        "",
        "MENU",
        "  Up/Down (or j/k) moves - Enter opens the highlighted entry.",
        "  Hotkeys: 1-9,0,a-f games - W search - H scores - T translator.",
        "  ? shows this help - q/Esc quits.",
        "",
        "WHILE PLAYING",
        "  Arrows/WASD play - p pauses - ? helps - q/Esc back to menu.",
        "  The bar at the bottom always lists the keys for that game.",
        "",
        "EXPLORE",
        "  Bored Wondering (W): search the web from inside the app.",
        "  High Scores (H): every best score, raw and in Bored Points.",
        "  Score Translator (T): convert any raw score to Bored Points.",
        "",
        "GAMES",
    ]
    for mod in game_mods:
        lines.append("  %-12s  %s" % (mod.TITLE, mod.DESCRIPTION))
        lines.append("     keys: %s" % mod.CONTROLS)
    lines += [
        "",
        "TIPS",
        "  Too small? Stretch the window to at least 80x24.",
        "  Colors missing? The app falls back to plain text, still playable.",
    ]
    return lines


def show_help(win, game_mods):
    top = 0
    lines = build_help_lines(game_mods)
    while True:
        if ui.too_small(win):
            ui.show_too_small(win)
            try:
                key = win.getch()
            except curses.error:
                key = -1
            if key in ui.QUIT_KEYS:
                return
            continue
        try:
            win.clear()
            h, w = win.getmaxyx()
            ui.header(win, "GAMEBORED HELP", "everything, on one screen")
            visible = max(1, h - 4)
            for i in range(visible):
                idx = top + i
                if idx >= len(lines):
                    break
                ln = lines[idx]
                attr = ui.color(7)
                if ln in ("MENU", "WHILE PLAYING", "GAMES", "EXPLORE", "TIPS"):
                    attr = ui.color(3) | curses.A_BOLD
                ui.safe_addstr(win, 2 + i, 3, ln[: w - 6], attr)
            if top + visible < len(lines):
                ui.safe_addstr(win, h - 2, w - 14, "(more: Up/Down)", ui.color(3))
            ui.footer(win, "Up/Down scroll | q/Esc back to menu")
            win.refresh()
        except curses.error:
            pass
        try:
            key = win.getch()
        except curses.error:
            key = -1
        if key in ui.QUIT_KEYS or key in (10, 13, curses.KEY_ENTER, 32):
            return
        if key == curses.KEY_UP:
            top = max(0, top - 1)
        elif key == curses.KEY_DOWN:
            top = min(max(0, len(lines) - 1), top + 1)
        elif key == curses.KEY_RESIZE:
            continue
