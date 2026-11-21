"""To-do list app: add, check off, delete. Persisted in the data dir."""

import curses

from . import storage as storage_mod
from . import ui

TITLE = "To-do"
DESCRIPTION = "Stuff to get done"
CONTROLS = "Up/Down pick | a add | Space check | d delete | q menu"
GAME_ID = "todo"
CATEGORY = "Tools"

FILE_NAME = "todos.json"
TEXT_LIMIT = 60


def load_todos(path=None):
    raw = storage_mod.load_json(FILE_NAME, [],
                                path=path or storage_mod.data_path(FILE_NAME))
    if not isinstance(raw, list):
        return []
    out = []
    for item in raw:
        if isinstance(item, dict):
            text = item.get("text")
            if isinstance(text, str) and text.strip():
                out.append({"text": text.strip()[:TEXT_LIMIT],
                            "done": bool(item.get("done"))})
        elif isinstance(item, str) and item.strip():
            out.append({"text": item.strip()[:TEXT_LIMIT], "done": False})
    return out


def save_todos(todos, path=None):
    clean = [{"text": t["text"], "done": bool(t["done"])}
             for t in (todos or []) if isinstance(t, dict) and t.get("text")]
    storage_mod.save_json(FILE_NAME, clean,
                          path=path or storage_mod.data_path(FILE_NAME))
    return clean


def add_todo(todos, text, path=None):
    todos = list(todos or [])
    if isinstance(text, str) and text.strip():
        todos.append({"text": text.strip()[:TEXT_LIMIT], "done": False})
        save_todos(todos, path=path)
    return todos


def toggle_todo(todos, index, path=None):
    todos = list(todos or [])
    if isinstance(index, int) and 0 <= index < len(todos):
        todos[index] = {"text": todos[index]["text"],
                        "done": not todos[index]["done"]}
        save_todos(todos, path=path)
    return todos


def delete_todo(todos, index, path=None):
    todos = list(todos or [])
    if isinstance(index, int) and 0 <= index < len(todos):
        del todos[index]
        save_todos(todos, path=path)
    return todos


def _prompt(win, prompt):
    buf = ""
    try:
        win.timeout(-1)
    except curses.error:
        pass
    while True:
        try:
            win.clear()
            h, w = win.getmaxyx()
            ui.header(win, prompt, "Enter adds | Esc cancels")
            ui.safe_addstr(win, 3, 2, (buf + "_")[: max(0, w - 4)],
                           curses.A_BOLD | ui.color(3))
            win.refresh()
        except curses.error:
            pass
        try:
            key = win.getch()
        except curses.error:
            key = -1
        if key == 27:
            return None
        if key in (10, 13, curses.KEY_ENTER):
            return buf.strip()
        if key in (curses.KEY_BACKSPACE, 127, 8):
            buf = buf[:-1]
        elif 32 <= key <= 126 and len(buf) < TEXT_LIMIT:
            buf += chr(key)


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
    todos = load_todos()
    sel = 0
    while True:
        sel = max(0, min(sel, max(0, len(todos) - 1)))
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
            open_n = sum(1 for t in todos if not t["done"])
            ui.header(stdscr, "TO-DO LIST",
                      "%d open, %d done" % (open_n, len(todos) - open_n))
            if not todos:
                ui.centered(stdscr, h // 2 - 1, "Nothing to do. Lucky you!",
                            ui.color(7) | curses.A_BOLD)
                ui.centered(stdscr, h // 2, "Press a to add a task.",
                            ui.color(3))
            visible = max(1, h - 5)
            top = max(0, min(sel - visible // 2, len(todos) - visible))
            row = 2
            for i in range(top, min(len(todos), top + visible)):
                if row >= h - 2:
                    break
                box = "[x]" if todos[i]["done"] else "[ ]"
                line = "%s %s %s" % (">" if i == sel else " ", box,
                                     todos[i]["text"])
                attr = (curses.A_REVERSE | curses.A_BOLD if i == sel
                        else (ui.color(2) if todos[i]["done"] else ui.color(7)))
                ui.safe_addstr(stdscr, row, 2, line[: w - 4], attr)
                row += 1
            ui.game_footer(stdscr, CONTROLS)
            stdscr.refresh()
        except curses.error:
            pass
        try:
            key = stdscr.getch()
        except curses.error:
            key = -1
        if key in ui.QUIT_KEYS:
            return
        if key == curses.KEY_RESIZE:
            continue
        if key in ui.HELP_KEYS:
            ui.show_help_overlay(stdscr, TITLE, CONTROLS)
            continue
        if key in (ord("a"), ord("A")):
            text = _prompt(stdscr, "NEW TASK:")
            if text:
                todos = add_todo(todos, text)
                sel = len(todos) - 1
            continue
        if not todos:
            continue
        if key == curses.KEY_UP:
            sel = (sel - 1) % len(todos)
        elif key == curses.KEY_DOWN:
            sel = (sel + 1) % len(todos)
        elif key in (ord(" "), ord("x"), ord("X"), 10, 13, curses.KEY_ENTER):
            todos = toggle_todo(todos, sel)
        elif key in (ord("d"), ord("D"), curses.KEY_DC):
            todos = delete_todo(todos, sel)
            sel = max(0, sel - 1)
