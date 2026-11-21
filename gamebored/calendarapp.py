"""Calendar app: month view with arrow-key navigation.

Left/right moves the selected day, up/down moves a week, PgUp/PgDn (or
, / .) changes the month, t jumps back to today. Pure date math lives in
headless helpers so it is unit-testable.
"""

import calendar
import curses
import datetime

from . import ui

TITLE = "Calendar"
DESCRIPTION = "Month at a glance"
CONTROLS = ("Arrows move day | PgUp/PgDn month | t today | q menu")
GAME_ID = "calendar"
CATEGORY = "Tools"


def month_grid(year, month):
    """Weeks of (year, month, day); day 0 pads days from other months."""
    try:
        year = int(year)
        month = int(month)
        if not 1 <= month <= 12:
            month = 1
    except (TypeError, ValueError):
        year, month = 2000, 1
    cal = calendar.Calendar(firstweekday=0)
    return [[(d.year, d.month, d.day) if d.month == month else (0, 0, 0)
             for d in week]
            for week in cal.monthdatescalendar(year, month)]


def shift_month(year, month, delta):
    """Move (year, month) by delta months. Never raises."""
    try:
        year, month, delta = int(year), int(month), int(delta)
    except (TypeError, ValueError):
        return (2000, 1)
    total = (year * 12 + (month - 1)) + delta
    total = max(0, total)
    return (total // 12, total % 12 + 1)


def move_day(year, month, day, direction):
    """Move the selection; may cross month borders. Never raises."""
    try:
        current = datetime.date(int(year), int(month), int(day))
    except (TypeError, ValueError):
        today = datetime.date.today()
        return (today.year, today.month, today.day)
    steps = {"left": -1, "right": 1, "up": -7, "down": 7}.get(direction, 0)
    try:
        moved = current + datetime.timedelta(days=steps)
    except OverflowError:
        return (current.year, current.month, current.day)
    return (moved.year, moved.month, moved.day)


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
    today = datetime.date.today()
    year, month, day = today.year, today.month, today.day
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
        weeks = month_grid(year, month)
        try:
            stdscr.clear()
            h, w = stdscr.getmaxyx()
            ui.header(stdscr, calendar.month_name[month] + " %d" % year,
                      today.strftime("%A, %B %d, %Y"))
            y = 3
            ui.safe_addstr(stdscr, y, max(2, (w - 28) // 2),
                           "Mo Tu We Th Fr Sa Su", ui.color(6) | curses.A_BOLD)
            y += 1
            for week in weeks:
                x = max(2, (w - 28) // 2)
                for wy, wm, wd in week:
                    if wd == 0:
                        label = "   "
                        attr = 0
                    else:
                        label = "%2d " % wd
                        attr = ui.color(7)
                        if (wy, wm, wd) == (today.year, today.month,
                                            today.day):
                            attr = ui.color(2) | curses.A_BOLD
                        if (wy, wm, wd) == (year, month, day):
                            attr = curses.A_REVERSE | curses.A_BOLD
                    ui.safe_addstr(stdscr, y, x, label, attr)
                    x += 3
                y += 1
                if y >= h - 2:
                    break
            picked = datetime.date(year, month, day).strftime("%A, %B %d")
            ui.centered(stdscr, h - 3, picked, ui.color(3) | curses.A_BOLD)
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
        if key == curses.KEY_LEFT:
            year, month, day = move_day(year, month, day, "left")
        elif key == curses.KEY_RIGHT:
            year, month, day = move_day(year, month, day, "right")
        elif key == curses.KEY_UP:
            year, month, day = move_day(year, month, day, "up")
        elif key == curses.KEY_DOWN:
            year, month, day = move_day(year, month, day, "down")
        elif key in (curses.KEY_PPAGE, ord(",")):
            year, month = shift_month(year, month, -1)[:2]
            day = min(day, calendar.monthrange(year, month)[1])
        elif key in (curses.KEY_NPAGE, ord(".")):
            year, month = shift_month(year, month, 1)[:2]
            day = min(day, calendar.monthrange(year, month)[1])
        elif key in (ord("t"), ord("T")):
            today = datetime.date.today()
            year, month, day = today.year, today.month, today.day
