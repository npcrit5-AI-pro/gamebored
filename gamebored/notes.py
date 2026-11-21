"""Notes app: create, list, open, edit, rename, delete with autosave.

Each note is a plain .txt file under the data dir's notes/ folder.
Editing is a real multi-line editor (arrows, backspace, enter, home/end)
and every keystroke autosaves. Only the standard library is used.
"""

import curses
import os
import re
import time

from . import storage as storage_mod
from . import ui

TITLE = "Notes"
DESCRIPTION = "Jot it down, keep it"
CONTROLS = ("Up/Down pick | Enter open | n new | r rename | d delete | "
            "q menu")
EDIT_CONTROLS = ("Arrows move | Enter split | Backspace join | "
                 "Home/End | Esc save+close")
DIR_NAME = "notes"
TITLE_LIMIT = 40


def notes_dir(path=None):
    root = path or os.path.join(storage_mod.app_dir(), DIR_NAME)
    try:
        os.makedirs(root, exist_ok=True)
    except OSError:
        pass
    return root


def _slug(name):
    base = re.sub(r"[^A-Za-z0-9 _-]+", "", name or "").strip()
    base = re.sub(r"\s+", "-", base).strip("-_") or "note"
    return base[:TITLE_LIMIT]


def _unique_path(root, slug, skip=None):
    candidate = os.path.join(root, slug + ".txt")
    if skip and os.path.abspath(candidate) == os.path.abspath(skip):
        return candidate
    n = 2
    while os.path.exists(candidate):
        candidate = os.path.join(root, "%s-%d.txt" % (slug, n))
        n += 1
        if n > 9999:
            break
    return candidate


def list_notes(path=None):
    """Sorted [(filename, title, mtime)] newest first. Never raises."""
    root = notes_dir(path)
    out = []
    try:
        names = os.listdir(root)
    except OSError:
        return []
    for name in names:
        if not name.endswith(".txt"):
            continue
        full = os.path.join(root, name)
        try:
            if not os.path.isfile(full):
                continue
            with open(full, "r", encoding="utf-8") as fh:
                first = fh.readline().strip()
            title = first[:TITLE_LIMIT] or os.path.splitext(name)[0]
            out.append((name, title, os.path.getmtime(full)))
        except (OSError, ValueError):
            continue
    out.sort(key=lambda item: item[2], reverse=True)
    return out


def read_note(root, filename):
    full = os.path.join(root, filename)
    try:
        with open(full, "r", encoding="utf-8") as fh:
            return fh.read()
    except (OSError, ValueError):
        return ""


def write_note(root, filename, text):
    """Atomically write a note file. Never raises."""
    full = os.path.join(root, filename)
    tmp = full + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(text if isinstance(text, str) else "")
            fh.flush()
            try:
                os.fsync(fh.fileno())
            except OSError:
                pass
        os.replace(tmp, full)
        return True
    except (OSError, TypeError, ValueError):
        try:
            os.unlink(tmp)
        except OSError:
            pass
        return False


def create_note(title, root=None):
    """Create a note file; returns its filename (or '' on failure)."""
    base = notes_dir(root)
    slug = _slug(title)
    full = _unique_path(base, slug)
    try:
        with open(full, "x", encoding="utf-8") as fh:
            fh.write((title or "Untitled").strip() + "\n")
        return os.path.basename(full)
    except (OSError, ValueError):
        return ""


def rename_note(root, filename, new_title):
    """Rename a note file; returns the new filename ('' on failure)."""
    old = os.path.join(root, filename)
    if not os.path.isfile(old):
        return ""
    slug = _slug(new_title)
    new = _unique_path(root, slug, skip=old)
    try:
        os.rename(old, new)
        return os.path.basename(new)
    except OSError:
        return ""


def delete_note(root, filename):
    try:
        os.unlink(os.path.join(root, filename))
        return True
    except OSError:
        return False


class TextBuffer:
    """Headless multi-line editor state (no curses here: unit-testable)."""

    def __init__(self, text=""):
        self.lines = (text if isinstance(text, str) else "").split("\n")
        if not self.lines:
            self.lines = [""]
        self.row = len(self.lines) - 1
        self.col = len(self.lines[self.row])
        self.want_col = self.col

    def text(self):
        return "\n".join(self.lines)

    def _clamp(self):
        self.row = max(0, min(self.row, len(self.lines) - 1))
        self.col = max(0, min(self.col, len(self.lines[self.row])))

    def move(self, direction):
        """Move cursor: up/down/left/right/home/end. Returns True."""
        if direction == "left":
            if self.col > 0:
                self.col -= 1
            elif self.row > 0:
                self.row -= 1
                self.col = len(self.lines[self.row])
            self.want_col = self.col
        elif direction == "right":
            if self.col < len(self.lines[self.row]):
                self.col += 1
            elif self.row < len(self.lines) - 1:
                self.row += 1
                self.col = 0
            self.want_col = self.col
        elif direction == "up":
            if self.row > 0:
                self.row -= 1
                self.col = min(self.want_col, len(self.lines[self.row]))
        elif direction == "down":
            if self.row < len(self.lines) - 1:
                self.row += 1
                self.col = min(self.want_col, len(self.lines[self.row]))
        elif direction == "home":
            self.col = 0
            self.want_col = 0
        elif direction == "end":
            self.col = len(self.lines[self.row])
            self.want_col = self.col
        else:
            return False
        self._clamp()
        return True

    def insert(self, char):
        if not isinstance(char, str) or len(char) != 1:
            return False
        if ord(char) < 32 or ord(char) == 127:
            return False
        line = self.lines[self.row]
        self.lines[self.row] = line[:self.col] + char + line[self.col:]
        self.col += 1
        self.want_col = self.col
        return True

    def enter(self):
        line = self.lines[self.row]
        self.lines[self.row] = line[:self.col]
        self.lines.insert(self.row + 1, line[self.col:])
        self.row += 1
        self.col = 0
        self.want_col = 0

    def backspace(self):
        if self.col > 0:
            line = self.lines[self.row]
            self.lines[self.row] = line[:self.col - 1] + line[self.col:]
            self.col -= 1
            self.want_col = self.col
            return True
        if self.row > 0:
            prev_len = len(self.lines[self.row - 1])
            self.lines[self.row - 1] += self.lines.pop(self.row)
            self.row -= 1
            self.col = prev_len
            self.want_col = self.col
            return True
        return False

    def delete(self):
        line = self.lines[self.row]
        if self.col < len(line):
            self.lines[self.row] = line[:self.col] + line[self.col + 1:]
            return True
        if self.row < len(self.lines) - 1:
            self.lines[self.row] += self.lines.pop(self.row + 1)
            return True
        return False


def _confirm(win, prompt):
    """Yes/no confirm box. Returns True only on y/Y."""
    try:
        win.timeout(-1)
    except curses.error:
        pass
    while True:
        try:
            h, w = win.getmaxyx()
            text = "%s (y/n)" % prompt
            box_w = min(max(len(text) + 6, 24), w - 2)
            y0 = max(0, h // 2 - 1)
            x0 = max(0, (w - box_w) // 2)
            ui.draw_frame(win, y0, x0, 3, box_w, title="!")
            ui.centered(win, y0 + 1, text[:box_w], curses.A_BOLD)
            win.refresh()
        except curses.error:
            pass
        try:
            key = win.getch()
        except curses.error:
            key = -1
        if key in (ord("y"), ord("Y")):
            return True
        if key in (ord("n"), ord("N"), 27, ord("q")):
            return False
        if key == curses.KEY_RESIZE:
            continue


def _prompt(win, prompt, initial=""):
    """One-line text prompt. Returns the string, or None on Esc."""
    buf = initial or ""
    try:
        win.timeout(-1)
    except curses.error:
        pass
    while True:
        try:
            win.clear()
            h, w = win.getmaxyx()
            ui.header(win, prompt, "Enter saves | Esc cancels")
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
        elif 32 <= key <= 126 and len(buf) < 60:
            buf += chr(key)


def _edit_note(win, root, filename):
    buf = TextBuffer(read_note(root, filename))
    top = 0
    try:
        curses.curs_set(1)
    except curses.error:
        pass
    try:
        win.keypad(True)
        win.timeout(-1)
    except curses.error:
        pass
    last_saved = ""
    while True:
        if ui.too_small(win, 12, 50):
            ui.show_too_small(win)
            try:
                key = win.getch()
            except curses.error:
                key = -1
            if key in ui.QUIT_KEYS:
                write_note(root, filename, buf.text())
                return
            continue
        try:
            win.clear()
            h, w = win.getmaxyx()
            title = filename[:-4] if filename.endswith(".txt") else filename
            ui.header(win, "NOTE: %s" % title[: max(0, w - 10)], EDIT_CONTROLS)
            view_h = max(1, h - 4)
            if buf.row < top:
                top = buf.row
            elif buf.row >= top + view_h:
                top = buf.row - view_h + 1
            for i in range(view_h):
                idx = top + i
                if idx >= len(buf.lines):
                    break
                ui.safe_addstr(win, 2 + i, 1,
                               buf.lines[idx][: max(0, w - 2)], ui.color(7))
            try:
                win.move(2 + buf.row - top, 1 + min(buf.col, max(0, w - 2)))
            except curses.error:
                pass
            status = "autosaved" if last_saved == buf.text() else "saving..."
            ui.footer(win, "%s | Esc save+close" % status)
            win.refresh()
        except curses.error:
            pass
        try:
            key = win.getch()
        except curses.error:
            key = -1
        if key == 27:  # Esc saves (autosave already did) and closes
            write_note(root, filename, buf.text())
            return
        if key == curses.KEY_RESIZE:
            continue
        if key == curses.KEY_UP:
            buf.move("up")
        elif key == curses.KEY_DOWN:
            buf.move("down")
        elif key == curses.KEY_LEFT:
            buf.move("left")
        elif key == curses.KEY_RIGHT:
            buf.move("right")
        elif key == curses.KEY_HOME:
            buf.move("home")
        elif key in (curses.KEY_END, 360):  # End / Shift-End
            buf.move("end")
        elif key in (10, 13, curses.KEY_ENTER):
            buf.enter()
        elif key in (curses.KEY_BACKSPACE, 127, 8):
            buf.backspace()
        elif key == curses.KEY_DC:
            buf.delete()
        elif 32 <= key <= 126:
            buf.insert(chr(key))
        else:
            continue
        # autosave after every change
        current = buf.text()
        if current != last_saved:
            if write_note(root, filename, current):
                last_saved = current
    # unreachable


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
    root = notes_dir()
    sel = 0
    while True:
        items = list_notes(root)
        sel = max(0, min(sel, max(0, len(items) - 1)))
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
            ui.header(stdscr, "NOTES", "%d saved" % len(items))
            if not items:
                ui.centered(stdscr, h // 2 - 1, "No notes yet.",
                            ui.color(7) | curses.A_BOLD)
                ui.centered(stdscr, h // 2,
                            "Press n to write your first one!",
                            ui.color(3))
            visible = max(1, h - 5)
            top = max(0, min(sel - visible // 2, len(items) - visible))
            row = 2
            for i in range(top, min(len(items), top + visible)):
                if row >= h - 2:
                    break
                name, title, mtime = items[i]
                stamp = time.strftime("%m-%d %H:%M",
                                      time.localtime(mtime))
                line = "%s  %-34s %s" % (">" if i == sel else " ",
                                         title[:34], stamp)
                attr = (curses.A_REVERSE | curses.A_BOLD if i == sel
                        else ui.color(7))
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
        if key in (ord("n"), ord("N")):
            name = _prompt(stdscr, "NEW NOTE: title?")
            if name:
                created = create_note(name, root)
                if created:
                    sel = 0
                    _edit_note(stdscr, root, created)
            try:
                curses.curs_set(0)
            except curses.error:
                pass
            continue
        if not items:
            continue
        if key == curses.KEY_UP:
            sel = (sel - 1) % len(items)
        elif key == curses.KEY_DOWN:
            sel = (sel + 1) % len(items)
        elif key in (10, 13, curses.KEY_ENTER, ord(" ")):
            _edit_note(stdscr, root, items[sel][0])
            try:
                curses.curs_set(0)
            except curses.error:
                pass
        elif key in (ord("r"), ord("R")):
            name = _prompt(stdscr, "RENAME NOTE:",
                           items[sel][0][:-4].replace("-", " "))
            if name:
                new = rename_note(root, items[sel][0], name)
                if new:
                    sel = 0
            try:
                curses.curs_set(0)
            except curses.error:
                pass
        elif key in (ord("d"), ord("D"), curses.KEY_DC):
            if _confirm(stdscr, "Delete '%s'?" % items[sel][1][:30]):
                delete_note(root, items[sel][0])
                sel = max(0, sel - 1)
            try:
                curses.curs_set(0)
            except curses.error:
                pass
