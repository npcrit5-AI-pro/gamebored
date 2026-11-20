"""GameBored main menu: pick a game, play, come back, quit with q/Esc.

The menu lists 15 games plus two extras: a High Scores table (every raw
best translated into Bored Points, with a combined all-games total) and
a Score Translator (pick a game, type any raw number, see the BP value).
"""

import curses
import traceback

from . import scores as scores_mod
from . import translator as translator_mod
from . import ui
from .games import GAMES

LOGO = [
    "  ____                         ___                         _ ",
    " / ___| __ _ _ __ ___   ___   | _ )  ___  _ _ ___  ___  __| |",
    "| |  _ / _` | '_ ` _ \\ / _ \\  | _ \\ / _ \\| '_/ _ \\/ _ \\/ _` |",
    "| |_| | (_| | | | | | |  __/  | _ /| (_) | | |  __/  __/ (_| |",
    " \\____|\\__,_|_| |_| |_|\\___|  |___/ \\___/|_| \\___|\\___|\\__,_|",
]

MENU_HINT = ("Up/Down select | 1-9,0,a-e play | H scores | T translator "
             "| q/Esc quit")


def menu_entries():
    """Return [(key_hint, kind, game_index_or_None)]."""
    entries = []
    for i in range(len(GAMES)):
        if i < 9:
            hint = str(i + 1)
        elif i == 9:
            hint = "0"
        else:
            hint = chr(ord("a") + i - 10)
        entries.append((hint, "game", i))
    entries.append(("H", "scores", None))
    entries.append(("T", "translator", None))
    return entries


ENTRIES = None


def get_entries():
    global ENTRIES
    if ENTRIES is None:
        ENTRIES = menu_entries()
    return ENTRIES


def shortcut_index(key):
    """Map a pressed key to an entry index, or None."""
    entries = get_entries()
    if ord("1") <= key <= ord("9"):
        idx = key - ord("1")
        if idx < len(entries):
            return idx
    elif key == ord("0"):
        if len(entries) > 9:
            return 9
    elif key in (ord("a"), ord("b"), ord("c"), ord("d"), ord("e"),
                 ord("A"), ord("B"), ord("C"), ord("D"), ord("E")):
        idx = 10 + (key | 32) - ord("a")
        if idx < len(entries):
            return idx
    elif key in (ord("h"), ord("H")):
        return len(entries) - 2
    elif key in (ord("t"), ord("T")):
        return len(entries) - 1
    return None


def _commas(n):
    s = "%d" % int(n)
    out = ""
    while len(s) > 3:
        out = "," + s[-3:] + out
        s = s[:-3]
    return s + out


def game_label(mod, score_store, width):
    entry = scores_mod.get_entry(score_store, mod.GAME_ID)
    bp = translator_mod.to_bp(mod.GAME_ID, entry["high"])
    text = "%-12s  %-24s  best:%-6d %s BP" % (
        mod.TITLE, mod.DESCRIPTION[:24], entry["high"], _commas(bp))
    return text[:max(0, width)]


def draw_menu(win, selected, score_store):
    entries = get_entries()
    try:
        win.clear()
    except curses.error:
        pass
    h, w = win.getmaxyx()
    y = 1
    for line in LOGO:
        if y < h - 1:
            ui.centered(win, y, line[: w - 2], ui.color(1) | curses.A_BOLD)
            y += 1
    y += 1
    if y < h:
        ui.centered(win, y, "Bored? Game on! Pick a game:",
                    ui.color(3) | curses.A_BOLD)
        y += 1
    top = y
    footer_rows = 4
    visible = max(1, h - top - footer_rows)
    start = max(0, min(selected - visible // 2, len(entries) - visible))
    end = min(len(entries), start + visible)
    start = max(0, end - visible)
    row = top
    for idx in range(start, end):
        hint, kind, gi = entries[idx]
        if row >= h - footer_rows:
            break
        if kind == "game":
            mod = GAMES[gi]
            label = " %s  %s" % (hint, game_label(mod, score_store, w - 8))
        elif kind == "scores":
            label = " %s  High Scores   every best in raw + Bored Points" % hint
        else:
            label = " %s  Score Translator   raw number -> BP for any game" % hint
        label = label[: max(0, w - 4)]
        x = max(0, (w - len(label)) // 2)
        if idx == selected:
            attr = curses.A_REVERSE | curses.A_BOLD
        elif kind == "game":
            attr = ui.color((gi % 6) + 1)
        else:
            attr = ui.color(3) | curses.A_BOLD
        ui.safe_addstr(win, row, x, label, attr)
        row += 1
    if start > 0 and top < h:
        ui.safe_addstr(win, top, max(0, w // 2 - 6), "...more...",
                       ui.color(7))
    # total BP line
    if h - 3 >= 0:
        total = translator_mod.total_bp(score_store)
        ui.centered(win, h - 3, "Combined total: %s BP across %d games" % (
            _commas(total), len(GAMES)), ui.color(2) | curses.A_BOLD)
    # controls line for the highlighted entry
    if h - 2 >= 0:
        hint, kind, gi = entries[selected]
        if kind == "game":
            detail = GAMES[gi].CONTROLS
        elif kind == "scores":
            detail = "Every high score, raw and translated"
        else:
            detail = "Convert any raw score to Bored Points"
        ui.centered(win, h - 2, "Selected: %s" % detail[: w - 14],
                    ui.color(7))
    ui.footer(win, MENU_HINT)
    try:
        win.refresh()
    except curses.error:
        pass


def show_high_scores(win, score_store):
    """High-score table: every raw best AND its BP, plus combined total."""
    try:
        win.timeout(-1)
    except curses.error:
        pass
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
        except curses.error:
            pass
        h, w = win.getmaxyx()
        ui.centered(win, 1, "HIGH SCORES (raw -> Bored Points)",
                    ui.color(3) | curses.A_BOLD)
        row = 3
        for mod in GAMES:
            if row >= h - 3:
                break
            entry = scores_mod.get_entry(score_store, mod.GAME_ID)
            bp = translator_mod.to_bp(mod.GAME_ID, entry["high"])
            line = "%-12s  best %-8d -> %8s BP" % (
                mod.TITLE, entry["high"], _commas(bp))
            ui.centered(win, row, line[: w - 2], ui.color(7))
            row += 1
        total = translator_mod.total_bp(score_store)
        if row < h - 1:
            ui.centered(win, row + 1,
                        "COMBINED TOTAL: %s BP" % _commas(total),
                        ui.color(2) | curses.A_BOLD)
        ui.footer(win, "q/Esc back to menu")
        try:
            win.refresh()
        except curses.error:
            pass
        try:
            key = win.getch()
        except curses.error:
            key = -1
        if key in ui.QUIT_KEYS:
            return
        elif key == curses.KEY_RESIZE:
            continue


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
        except curses.error:
            pass
        h, w = win.getmaxyx()
        ui.centered(win, 1, "SCORE TRANSLATOR: pick a game",
                    ui.color(3) | curses.A_BOLD)
        top = 3
        visible = max(1, h - top - 3)
        start = max(0, min(sel - visible // 2, len(GAMES) - visible))
        end = min(len(GAMES), start + visible)
        start = max(0, end - visible)
        row = top
        for i in range(start, end):
            if i < 9:
                hint = str(i + 1)
            elif i == 9:
                hint = "0"
            else:
                hint = chr(ord("a") + i - 10)
            info = translator_mod.CONVERSIONS[GAMES[i].GAME_ID]
            line = " %s  %-12s  %s" % (hint, GAMES[i].TITLE, info["raw"])
            line = line[: w - 4]
            x = max(0, (w - len(line)) // 2)
            attr = (curses.A_REVERSE | curses.A_BOLD if i == sel
                    else ui.color((i % 6) + 1))
            ui.safe_addstr(win, row, x, line, attr)
            row += 1
        ui.footer(win, "1-9,0,a-e or arrows+Enter pick | q back")
        try:
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
        else:
            idx = shortcut_index(key)
            if idx is not None and idx < len(GAMES):
                return idx


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
        except curses.error:
            pass
        h, w = win.getmaxyx()
        ui.centered(win, 1, "SCORE TRANSLATOR: %s" % mod.TITLE,
                    ui.color(3) | curses.A_BOLD)
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
        ui.footer(win, "digits type | Enter converts | q back")
        try:
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
        elif ord("0") <= key <= ord("9") and len(buf) < 9:
            buf += chr(key)


def show_translator(win):
    while True:
        idx = _pick_translator_game(win)
        if idx is None:
            return
        _translator_prompt(win, idx)


def menu_loop(stdscr):
    curses.curs_set(0)
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
    entries = get_entries()
    selected = 0
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
        draw_menu(stdscr, selected, score_store)
        try:
            key = stdscr.getch()
        except curses.error:
            key = -1
        if key in ui.QUIT_KEYS:
            return
        elif key == curses.KEY_UP:
            selected = (selected - 1) % len(entries)
        elif key == curses.KEY_DOWN:
            selected = (selected + 1) % len(entries)
        elif key in (10, 13, curses.KEY_ENTER, ord(" ")):
            selected = activate(stdscr, selected, score_store)
            score_store = scores_mod.load()
        elif key == curses.KEY_RESIZE:
            continue
        else:
            idx = shortcut_index(key)
            if idx is not None:
                selected = activate(stdscr, idx, score_store)
                score_store = scores_mod.load()


def activate(stdscr, idx, score_store):
    entries = get_entries()
    hint, kind, gi = entries[idx]
    if kind == "game":
        launch(stdscr, gi, score_store)
    elif kind == "scores":
        show_high_scores(stdscr, score_store)
    else:
        show_translator(stdscr)
    return idx


def launch(stdscr, idx, score_store):
    mod = GAMES[idx]
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
