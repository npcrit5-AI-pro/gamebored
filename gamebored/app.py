"""GameBored main menu: pick a game, play, come back, quit with q/Esc."""

import curses
import traceback

from . import scores as scores_mod
from . import ui
from .games import GAMES

LOGO = [
    "  ____                         ___                         _ ",
    " / ___| __ _ _ __ ___   ___   | _ )  ___  _ _ ___  ___  __| |",
    "| |  _ / _` | '_ ` _ \\ / _ \\  | _ \\ / _ \\| '_/ _ \\/ _ \\/ _` |",
    "| |_| | (_| | | | | | |  __/  | _ /| (_) | | |  __/  __/ (_| |",
    " \\____|\\__,_|_| |_| |_|\\___|  |___/ \\___/|_| \\___|\\___|\\__,_|",
]

MENU_HINT = "Up/Down select  |  Enter/1-9,0 play  |  q/Esc quit"


def draw_menu(win, selected, score_store):
    try:
        win.clear()
    except curses.error:
        pass
    h, w = win.getmaxyx()
    y = max(1, min(2, h - len(GAMES) - 10))
    for line in LOGO:
        if y < h - 1:
            ui.centered(win, y, line[: w - 2], ui.color(1) | curses.A_BOLD)
            y += 1
    y += 1
    if y < h:
        ui.centered(win, y, "Bored? Game on! Pick a game:",
                    ui.color(3) | curses.A_BOLD)
        y += 2
    for i, mod in enumerate(GAMES):
        if y >= h - 2:
            break
        entry = scores_mod.get_entry(score_store, mod.GAME_ID)
        key = str(i + 1) if i < 9 else "0"
        label = " %s  %-12s  %-28s  best:%-5d" % (
            key, mod.TITLE, mod.DESCRIPTION[:28], entry["high"])
        label = label[: max(0, w - 4)]
        x = max(0, (w - len(label)) // 2)
        attr = curses.A_REVERSE | curses.A_BOLD if i == selected else 0
        if i != selected:
            attr = ui.color((i % 6) + 1)
        ui.safe_addstr(win, y, x, label, attr)
        y += 1
    # controls line for the highlighted game
    if y + 1 < h:
        ui.centered(win, h - 3, "Selected: %s" % GAMES[selected].CONTROLS[: w - 14],
                    ui.color(7))
    ui.footer(win, MENU_HINT)
    try:
        win.refresh()
    except curses.error:
        pass


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
            selected = (selected - 1) % len(GAMES)
        elif key == curses.KEY_DOWN:
            selected = (selected + 1) % len(GAMES)
        elif key in (10, 13, curses.KEY_ENTER, ord(" ")):
            launch(stdscr, selected, score_store)
            score_store = scores_mod.load()
        elif ord("1") <= key <= ord("9"):
            idx = key - ord("1")
            if idx < len(GAMES):
                launch(stdscr, idx, score_store)
                score_store = scores_mod.load()
        elif key == ord("0"):
            if len(GAMES) >= 10:
                launch(stdscr, 9, score_store)
                score_store = scores_mod.load()
        elif key == curses.KEY_RESIZE:
            continue


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
