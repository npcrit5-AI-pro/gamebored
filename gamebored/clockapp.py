"""Clock app: wall clock, stopwatch, and countdown timer.

Three modes on one screen (1/2/3 to switch). The stopwatch and timer tick
without freezing the UI; q/Esc always backs out at once.
"""

import curses
import time

from . import ui

TITLE = "Clock"
DESCRIPTION = "Time, stopwatch, timer"
CONTROLS = "1 clock | 2 stopwatch | 3 timer | Space start/stop | r reset | q menu"
GAME_ID = "clock"
CATEGORY = "Tools"


def format_hms(total_seconds):
    """Format a duration as H:MM:SS (or M:SS under an hour). Never raises."""
    try:
        total = max(0, int(total_seconds))
    except (TypeError, ValueError, OverflowError):
        total = 0
    hours, rest = divmod(total, 3600)
    minutes, seconds = divmod(rest, 60)
    if hours:
        return "%d:%02d:%02d" % (hours, minutes, seconds)
    return "%d:%02d" % (minutes, seconds)


def parse_duration(text):
    """Parse 'mm:ss', 'ss', '1h2m3s' into seconds. None when invalid."""
    if not isinstance(text, str):
        return None
    text = text.strip().lower()
    if not text:
        return None
    if ":" in text:
        parts = text.split(":")
        if len(parts) > 3 or not all(p.isdigit() for p in parts):
            return None
        nums = [int(p) for p in parts]
        total = 0
        for n in nums:
            total = total * 60 + n
        return total if total > 0 else None
    digits = ""
    total = 0
    for ch in text:
        if ch.isdigit():
            digits += ch
        elif ch in ("h", "m", "s") and digits:
            scale = {"h": 3600, "m": 60, "s": 1}[ch]
            total += int(digits) * scale
            digits = ""
        else:
            return None
    if digits:
        total += int(digits)
    return total if total > 0 else None


def play(stdscr, _score_store=None):
    try:
        curses.curs_set(0)
    except curses.error:
        pass
    try:
        stdscr.keypad(True)
        stdscr.timeout(100)
    except curses.error:
        pass
    mode = "clock"
    sw_running, sw_start, sw_elapsed = False, 0.0, 0.0
    tm_total, tm_left, tm_running, tm_last = 300, 300.0, False, 0.0
    tm_buf, tm_edit = "", False
    tm_done = False
    while True:
        if ui.too_small(stdscr, 12, 50):
            ui.show_too_small(stdscr)
            try:
                key = stdscr.getch()
            except curses.error:
                key = -1
            if key in ui.QUIT_KEYS:
                return
            continue
        now = time.time()
        if sw_running:
            sw_show = sw_elapsed + (now - sw_start)
        else:
            sw_show = sw_elapsed
        if tm_running:
            tm_left -= now - tm_last
            tm_last = now
            if tm_left <= 0:
                tm_left = 0
                tm_running = False
                tm_done = True
                try:
                    curses.beep()
                except curses.error:
                    pass
        try:
            stdscr.clear()
            h, w = stdscr.getmaxyx()
            ui.header(stdscr, "CLOCK", "1 clock - 2 stopwatch - 3 timer")
            tabs = "[clock]" if mode == "clock" else " clock "
            tabs += "  "
            tabs += "[stopwatch]" if mode == "stop" else " stopwatch "
            tabs += "  "
            tabs += "[timer]" if mode == "timer" else " timer "
            ui.centered(stdscr, 3, tabs, ui.color(6) | curses.A_BOLD)
            if mode == "clock":
                stamp = time.strftime("%H:%M:%S")
                day = time.strftime("%A, %B %d")
                ui.centered(stdscr, h // 2 - 1, stamp,
                            ui.color(1) | curses.A_BOLD)
                ui.centered(stdscr, h // 2 + 1, day, ui.color(7))
            elif mode == "stop":
                ui.centered(stdscr, h // 2 - 1, format_hms(sw_show),
                            ui.color(1) | curses.A_BOLD)
                state = "RUNNING" if sw_running else "STOPPED"
                ui.centered(stdscr, h // 2 + 1,
                            "%s  (Space start/stop, r reset)" % state,
                            ui.color(3))
            else:
                ui.centered(stdscr, h // 2 - 1, format_hms(tm_left),
                            (ui.color(5) | curses.A_BOLD) if tm_done
                            else (ui.color(1) | curses.A_BOLD))
                if tm_edit:
                    ui.centered(stdscr, h // 2 + 1,
                                "Set: %s_  (mm:ss, Enter saves)" % tm_buf,
                                ui.color(3) | curses.A_BOLD)
                elif tm_done:
                    ui.centered(stdscr, h // 2 + 1, "TIME'S UP!",
                                ui.color(5) | curses.A_BOLD)
                else:
                    state = "RUNNING" if tm_running else "PAUSED"
                    ui.centered(stdscr, h // 2 + 1,
                                "%s  (Space start/stop, t set, r reset)"
                                % state, ui.color(3))
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
        if key in ui.HELP_KEYS and not tm_edit:
            ui.show_help_overlay(stdscr, TITLE, CONTROLS)
            try:
                stdscr.timeout(100)
            except curses.error:
                pass
            continue
        if tm_edit:
            if key in (10, 13, curses.KEY_ENTER):
                parsed = parse_duration(tm_buf)
                if parsed:
                    tm_total = parsed
                    tm_left = float(parsed)
                    tm_done = False
                    tm_running = False
                tm_edit = False
                tm_buf = ""
            elif key == 27:
                tm_edit = False
                tm_buf = ""
            elif key in (curses.KEY_BACKSPACE, 127, 8):
                tm_buf = tm_buf[:-1]
            elif 32 <= key <= 126 and len(tm_buf) < 12:
                tm_buf += chr(key)
            continue
        if key == ord("1"):
            mode = "clock"
        elif key == ord("2"):
            mode = "stop"
        elif key == ord("3"):
            mode = "timer"
        elif key == ord(" "):
            if mode == "stop":
                if sw_running:
                    sw_elapsed = sw_elapsed + (time.time() - sw_start)
                    sw_running = False
                else:
                    sw_start = time.time()
                    sw_running = True
            elif mode == "timer" and not tm_done:
                if tm_running:
                    tm_running = False
                elif tm_left > 0:
                    tm_running = True
                    tm_last = time.time()
        elif key in (ord("r"), ord("R")):
            if mode == "stop":
                sw_running, sw_elapsed = False, 0.0
            elif mode == "timer":
                tm_running, tm_left, tm_done = False, float(tm_total), False
        elif key in (ord("t"), ord("T")) and mode == "timer":
            tm_edit, tm_buf, tm_running = True, "", False
