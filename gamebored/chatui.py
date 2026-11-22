"""Shared scrollable chat UI for GameBored Talk apps.

ELIZA and PARRY share one look: a scrollable transcript, a typing line,
and a footer with keys. Only the standard library is used.
"""

import curses
import textwrap

from . import ui

INPUT_LIMIT = 200
HISTORY_LIMIT = 50


def wrap_message(who, text, width):
    """Wrap one chat message into display lines. Headless-testable."""
    width = max(20, int(width or 80) - 4)
    prefix = "%s: " % who if who else ""
    try:
        lines = textwrap.wrap(str(text), width - len(prefix),
                              break_long_words=True,
                              break_on_hyphens=False) or [""]
    except Exception:
        lines = [str(text)]
    out = [prefix + lines[0]]
    pad = " " * len(prefix)
    out.extend(pad + ln for ln in lines[1:])
    return out


def flatten(transcript, width):
    """Whole transcript as display lines. Headless-testable."""
    lines = []
    for who, text in transcript or []:
        try:
            lines.extend(wrap_message(who, text, width))
        except Exception:
            continue
    return lines


def visible_lines(all_lines, height, scroll):
    """Window of lines to show; scroll=0 means pinned to the bottom."""
    height = max(1, int(height))
    scroll = max(0, int(scroll or 0))
    if len(all_lines) <= height:
        return list(all_lines)
    start = max(0, len(all_lines) - height - scroll)
    return all_lines[start:start + height]


def draw(win, title, subtitle, transcript, scroll, input_buf,
         extra_header=(), footer=None):
    """Render the chat screen. Never raises."""
    try:
        win.clear()
    except curses.error:
        pass
    try:
        h, w = win.getmaxyx()
    except curses.error:
        return scroll
    try:
        ui.header(win, title, subtitle)
    except curses.error:
        pass
    y = 2
    for line in extra_header or []:
        if y >= h - 3:
            break
        try:
            ui.safe_addstr(win, y, 2, str(line)[: max(0, w - 4)],
                           ui.color(6) | curses.A_BOLD)
        except curses.error:
            pass
        y += 1
    top = y
    input_rows = 2
    avail = max(1, h - top - input_rows - 1)
    all_lines = flatten(transcript, w)
    max_scroll = max(0, len(all_lines) - avail)
    scroll = max(0, min(scroll, max_scroll))
    for i, line in enumerate(visible_lines(all_lines, avail, scroll)):
        attr = ui.color(7)
        try:
            if line.startswith("YOU:"):
                attr = ui.color(2)
            elif line.startswith("ELIZA:") or line.startswith("PARRY:"):
                attr = ui.color(3) | curses.A_BOLD
            elif line.startswith("*"):
                attr = ui.color(6)
        except curses.error:
            pass
        ui.safe_addstr(win, top + i, 2, line[: max(0, w - 4)], attr)
    if max_scroll > 0 and scroll > 0:
        ui.safe_addstr(win, top, max(0, w - 14), "[scroll %d]" % scroll,
                       ui.color(6))
    try:
        ui.safe_addstr(win, h - 3, 2, ("> " + input_buf + "_")[: max(0, w - 4)],
                       curses.A_BOLD | ui.color(1))
        if footer is None:
            footer = ("Enter send | PgUp/PgDn scroll | Up/Dn history | "
                      "help save quit | q menu")
        ui.footer(win, footer)
        win.refresh()
    except curses.error:
        pass
    return scroll


class InputState:
    """Single-line editor with history. Headless-testable."""

    def __init__(self):
        self.buf = ""
        self.history = []
        self.hist_idx = None

    def key(self, key):
        """Feed a key. Returns 'submit' when Enter is pressed."""
        if key in (10, 13, curses.KEY_ENTER):
            return "submit"
        if key in (curses.KEY_BACKSPACE, 127, 8):
            self.buf = self.buf[:-1]
            self.hist_idx = None
        elif key == curses.KEY_DC:
            self.buf = self.buf[:-1]
            self.hist_idx = None
        elif key == curses.KEY_UP:
            if self.history:
                if self.hist_idx is None:
                    self.hist_idx = len(self.history) - 1
                else:
                    self.hist_idx = max(0, self.hist_idx - 1)
                self.buf = self.history[self.hist_idx]
        elif key == curses.KEY_DOWN:
            if self.history and self.hist_idx is not None:
                if self.hist_idx >= len(self.history) - 1:
                    self.hist_idx = None
                    self.buf = ""
                else:
                    self.hist_idx += 1
                    self.buf = self.history[self.hist_idx]
        elif 32 <= key <= 126 and len(self.buf) < INPUT_LIMIT:
            self.buf += chr(key)
            self.hist_idx = None
        return None

    def submit(self):
        text = self.buf.strip()
        self.buf = ""
        self.hist_idx = None
        if text:
            self.history.append(text)
            del self.history[:-HISTORY_LIMIT]
        return text
