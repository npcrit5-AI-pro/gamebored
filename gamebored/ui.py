"""Shared curses UI helpers for GameBored.

Everything here degrades gracefully: small terminals get a friendly
'make the window bigger' message instead of a curses crash, every
addstr/addch call is guarded against writing past the screen edge, and
all color use falls back to plain text when the terminal has no color.
"""

import curses

from . import translator as translator_mod

MIN_H = 24
MIN_W = 80

TITLE = "GAMEBORED"
QUIT_KEYS = (27, ord("q"), ord("Q"))  # Esc / q
PAUSE_KEYS = (ord("p"), ord("P"))
HELP_KEYS = (ord("?"),)

FOOTER_HELP = "Up/Down move | Enter open | 1-9,0/W/H/T/? shortcuts | q quit"
GAME_FOOTER_SUFFIX = "p pause | ? help | q menu"


def init_colors():
    """Set up color pairs. Safe to call when colors are unsupported."""
    try:
        if not curses.has_colors():
            return
        curses.start_color()
        try:
            curses.use_default_colors()
        except curses.error:
            pass
        pairs = [
            (1, curses.COLOR_CYAN, -1),
            (2, curses.COLOR_GREEN, -1),
            (3, curses.COLOR_YELLOW, -1),
            (4, curses.COLOR_MAGENTA, -1),
            (5, curses.COLOR_RED, -1),
            (6, curses.COLOR_BLUE, -1),
            (7, curses.COLOR_WHITE, -1),
            (8, curses.COLOR_BLACK, curses.COLOR_GREEN),
            (9, curses.COLOR_BLACK, curses.COLOR_YELLOW),
            (10, curses.COLOR_WHITE, curses.COLOR_RED),
            (11, curses.COLOR_WHITE, curses.COLOR_BLUE),
            (12, curses.COLOR_BLACK, curses.COLOR_CYAN),
        ]
        for num, fg, bg in pairs:
            try:
                curses.init_pair(num, fg, bg)
            except curses.error:
                pass
    except curses.error:
        pass


def has_color():
    """True when the terminal can actually show colors."""
    try:
        return bool(curses.has_colors())
    except curses.error:
        return False


def color(num):
    try:
        return curses.color_pair(num)
    except curses.error:
        return 0


def safe_addstr(win, y, x, text, attr=0):
    try:
        if not isinstance(text, str):
            try:
                text = str(text)
            except Exception:
                return
        h, w = win.getmaxyx()
        if y < 0 or y >= h or x >= w:
            return
        if x < 0:
            text = text[-x:]
            x = 0
        text = text[: max(0, w - x - 1)] if len(text) > w - x else text
        # curses refuses to write to the bottom-right corner; trim it.
        if y == h - 1 and x + len(text) >= w:
            text = text[: max(0, w - x - 1)]
        if not text:
            return
        win.addstr(y, x, text, attr)
    except (curses.error, TypeError, ValueError, OverflowError):
        pass


def safe_addch(win, y, x, ch, attr=0):
    try:
        if isinstance(ch, str):
            if len(ch) != 1:
                return
        elif isinstance(ch, int):
            if not 0 <= ch <= 255:
                return
        else:
            return
        h, w = win.getmaxyx()
        if y < 0 or y >= h or x < 0 or x >= w:
            return
        if y == h - 1 and x == w - 1:
            return
        win.addch(y, x, ch, attr)
    except (curses.error, TypeError, ValueError, OverflowError):
        pass


def too_small(win, min_h=MIN_H, min_w=MIN_W):
    try:
        h, w = win.getmaxyx()
        return h < min_h or w < min_w
    except curses.error:
        return True


def show_too_small(win, min_h=MIN_H, min_w=MIN_W):
    """Draw the friendly small-terminal message. Blocks until key/resize."""
    try:
        win.clear()
        h, w = win.getmaxyx()
        lines = [
            "Whoa, cozy terminal!",
            "",
            "GameBored needs at least %dx%d." % (min_w, min_h),
            "Make the window bigger to play.",
            "",
            "Press q to quit, any other key to retry.",
        ]
        box_w = min(max(len(ln) for ln in lines) + 6, max(10, w - 2))
        box_h = len(lines) + 2
        y0 = max(0, (h - box_h) // 2)
        x0 = max(0, (w - box_w) // 2)
        for i in range(box_h):
            safe_addstr(win, y0 + i, x0, " " * box_w, color(10))
        for i, line in enumerate(lines):
            attr = curses.A_BOLD
            if i == 0:
                attr |= color(3)
            centered(win, y0 + 1 + i, line[:box_w], attr)
        win.refresh()
    except curses.error:
        pass


def centered(win, y, text, attr=0):
    try:
        _, w = win.getmaxyx()
        safe_addstr(win, y, max(0, (w - len(text)) // 2), text, attr)
    except curses.error:
        pass


def footer(win, text):
    try:
        h, w = win.getmaxyx()
        safe_addstr(win, h - 1, 0, (" " + text)[: max(0, w - 1)], color(7))
    except curses.error:
        pass


def game_footer(win, controls):
    """Consistent in-game key-hint bar: controls + pause/help/menu keys."""
    footer(win, "%s  |  %s" % (controls, GAME_FOOTER_SUFFIX))


def header(win, title, subtitle=""):
    """Consistent screen header: bold title, optional dim subtitle."""
    try:
        centered(win, 0, title, color(1) | curses.A_BOLD)
        if subtitle:
            centered(win, 1, subtitle, color(7))
    except curses.error:
        pass


def draw_frame(win, y0, x0, box_h, box_w, title="", fill=None):
    """Draw a bordered panel. Never raises on small screens."""
    try:
        h, w = win.getmaxyx()
        y0 = max(0, y0)
        x0 = max(0, x0)
        box_h = min(box_h, h - y0)
        box_w = min(box_w, w - x0)
        if box_h < 3 or box_w < 4:
            return False
        if fill is not None:
            for i in range(box_h):
                safe_addstr(win, y0 + i, x0, " " * box_w, fill)
        # corners + edges
        safe_addch(win, y0, x0, ord("+"), color(1) | curses.A_BOLD)
        safe_addch(win, y0, x0 + box_w - 1, ord("+"), color(1) | curses.A_BOLD)
        safe_addch(win, y0 + box_h - 1, x0, ord("+"), color(1) | curses.A_BOLD)
        safe_addch(win, y0 + box_h - 1, x0 + box_w - 1, ord("+"),
                   color(1) | curses.A_BOLD)
        for x in range(1, box_w - 1):
            safe_addch(win, y0, x0 + x, ord("-"), color(1))
            safe_addch(win, y0 + box_h - 1, x0 + x, ord("-"), color(1))
        for y in range(1, box_h - 1):
            safe_addch(win, y0 + y, x0, ord("|"), color(1))
            safe_addch(win, y0 + y, x0 + box_w - 1, ord("|"), color(1))
        if title:
            label = " %s " % title[: max(0, box_w - 4)]
            safe_addstr(win, y0, x0 + max(1, (box_w - len(label)) // 2),
                        label, color(3) | curses.A_BOLD)
        return True
    except curses.error:
        return False


def pause_overlay(win, title="PAUSED"):
    """Show a pause panel. Returns 'quit' if the user wants the menu.

    Any of p/P/Enter/Space resumes; q/Esc quits to the menu. Resize just
    redraws the panel instead of crashing.
    """
    try:
        win.timeout(-1)
    except curses.error:
        pass
    while True:
        try:
            h, w = win.getmaxyx()
            box_w = min(44, w - 4)
            lines = [
                title,
                "",
                "Take a breather. Your game is waiting.",
                "",
                "p/Enter resume    q/Esc quit to menu",
            ]
            box_h = len(lines) + 2
            y0 = max(0, (h - box_h) // 2)
            x0 = max(0, (w - box_w) // 2)
            draw_frame(win, y0, x0, box_h, box_w, title="II")
            for i, ln in enumerate(lines):
                attr = curses.A_BOLD
                if i == 0:
                    attr |= color(3)
                centered(win, y0 + 1 + i, ln[:box_w], attr)
            footer(win, "p resume | q quit to menu")
            win.refresh()
        except curses.error:
            pass
        try:
            key = win.getch()
        except curses.error:
            key = -1
        if key in QUIT_KEYS:
            return "quit"
        if key in PAUSE_KEYS or key in (10, 13, 32, curses.KEY_ENTER):
            return "resume"
        if key == curses.KEY_RESIZE:
            continue
        if key != -1:
            return "resume"


HELP_LINES = [
    ("Move / pick", "Up/Down arrows (or j/k), Enter to open"),
    ("Hotkeys", "1-9,0,a-f games - W search - H scores - T points - ? this help"),
    ("In every game", "Arrows/WASD play - p pause - ? help - q/Esc menu"),
    ("Scores", "Best score per game is saved automatically"),
    ("Tiny window?", "Make it 80x24 or bigger; nothing breaks"),
]


def show_help_overlay(win, game_title="", controls=""):
    """Pop-up help panel used from the menu and inside every game."""
    try:
        win.timeout(-1)
    except curses.error:
        pass
    while True:
        try:
            h, w = win.getmaxyx()
            lines = ["GAMEBORED HELP", ""]
            for k, v in HELP_LINES:
                lines.append("%-12s  %s" % (k + ":", v))
            if game_title and controls:
                lines.append("")
                lines.append("%s: %s" % (game_title, controls))
            lines.append("")
            lines.append("Press any key to go back (q/Esc just closes this)")
            box_w = min(max(len(ln) for ln in lines) + 4, w - 2)
            box_h = min(len(lines) + 2, h)
            y0 = max(0, (h - box_h) // 2)
            x0 = max(0, (w - box_w) // 2)
            draw_frame(win, y0, x0, box_h, box_w, title="?")
            for i, ln in enumerate(lines):
                if y0 + 1 + i >= y0 + box_h - 1:
                    break
                attr = 0
                if i == 0:
                    attr = color(1) | curses.A_BOLD
                safe_addstr(win, y0 + 1 + i, x0 + 2, ln[: box_w - 4], attr)
            win.refresh()
        except curses.error:
            pass
        try:
            key = win.getch()
        except curses.error:
            key = -1
        if key == curses.KEY_RESIZE:
            continue
        if key != -1:
            return key


def game_over_screen(win, game_title, lines, score=None, best=None,
                     is_new_high=False, game_id=None, won=None):
    """Show a friendly game-over panel. Returns after any keypress.

    When game_id is given, score/best lines also show the translation into
    the universal Bored Points (BP) language, e.g. 'Score: 248 -> 1,240 BP'.
    """
    try:
        win.timeout(-1)
    except curses.error:
        pass
    try:
        h, w = win.getmaxyx()
        if won is True:
            headline = "YOU WIN!  %s" % game_title
            head_attr = color(2) | curses.A_BOLD
            flair = "Nicely played!"
        elif won is False:
            headline = "GAME OVER: %s" % game_title
            head_attr = color(5) | curses.A_BOLD
            flair = "Good try - one more run?"
        else:
            headline = "GAME OVER: %s" % game_title
            head_attr = color(3) | curses.A_BOLD
            flair = "Thanks for playing!"
        box_lines = [headline, flair, ""]
        for ln in lines:
            box_lines.append(ln)
        if score is not None:
            box_lines.append("")
            if game_id in (translator_mod.CONVERSIONS or {}):
                box_lines.append("Score: %s" % translator_mod.format_score(
                    game_id, score))
            else:
                box_lines.append("Score: %s" % score)
        if best is not None:
            if game_id in (translator_mod.CONVERSIONS or {}):
                box_lines.append("Best:  %s" % translator_mod.format_score(
                    game_id, best))
            else:
                box_lines.append("Best:  %s" % best)
        if is_new_high:
            box_lines.append("NEW HIGH SCORE!")
        box_lines.append("")
        box_lines.append("any key: back to menu")
        box_w = min(w - 4, max(40, max(len(ln) for ln in box_lines) + 6))
        box_h = min(len(box_lines) + 2, h)
        y0 = max(0, (h - box_h) // 2)
        x0 = max(0, (w - box_w) // 2)
        try:
            win.clear()
        except curses.error:
            pass
        draw_frame(win, y0, x0, box_h, box_w, title="*")
        for i, ln in enumerate(box_lines):
            if y0 + 1 + i >= y0 + box_h - 1:
                break
            attr = 0
            if i == 0:
                attr = head_attr
            elif ln == "NEW HIGH SCORE!":
                attr = color(3) | curses.A_BOLD | curses.A_BLINK
            elif ln == "any key: back to menu":
                attr = color(7)
            centered(win, y0 + 1 + i, ln[:box_w], attr)
        footer(win, "any key back to menu")
        win.refresh()
        while True:
            try:
                key = win.getch()
            except curses.error:
                key = -1
            if key == curses.KEY_RESIZE:
                return key
            if key != -1:
                return key
    except curses.error:
        return -1


def confirm_quit_game(win):
    """Not used as a popup; games quit directly on q/Esc for snappiness."""
    return True


_ARROW_TAILS = {65: 259, 66: 258, 67: 261, 68: 260}  # A/B/C/D -> up/dn/right/left


def _key_values(name):
    try:
        return getattr(curses, name)
    except AttributeError:
        return None


class InputWindow:
    """Proxy for a curses window that translates raw arrow-key sequences.

    curses with keypad(True) translates sequences matching terminfo, but
    mismatched TERM settings (common over SSH) can deliver a bare ESC
    followed by bytes curses does not recognize. Routing getch() through
    this proxy catches those so arrows work everywhere.
    """

    def __init__(self, win):
        self.__dict__["_win"] = win
        self.__dict__["_delay"] = -1

    def getch(self):
        return get_key(self.__dict__["_win"], self.__dict__["_delay"])

    def timeout(self, delay):
        self.__dict__["_delay"] = delay
        try:
            self.__dict__["_win"].timeout(delay)
        except curses.error:
            pass

    def nodelay(self, flag):
        self.__dict__["_delay"] = 0 if flag else -1
        try:
            self.__dict__["_win"].nodelay(bool(flag))
        except curses.error:
            pass

    def __getattr__(self, name):
        return getattr(self.__dict__["_win"], name)


def get_key(win, delay=-1):
    """Read one key, translating raw ESC-[ / ESC-O arrow sequences.

    curses with keypad(True) already translates sequences matching the
    terminfo entry, but odd terminals/terminfo combos can deliver a bare
    ESC followed by bytes curses does not recognize. This helper catches
    those so arrows keep working everywhere. `delay` is the getch timeout
    in ms (-1 blocks). Returns -1 on timeout, 27 for a lone Esc.
    """
    try:
        win.timeout(delay)
    except curses.error:
        pass
    try:
        key = win.getch()
    except curses.error:
        return -1
    if key != 27:
        return key
    # Possible escape sequence: peek briefly for the rest of it.
    try:
        win.timeout(60)
    except curses.error:
        pass
    tail = []
    for _ in range(2):
        try:
            nxt = win.getch()
        except curses.error:
            nxt = -1
        if nxt == -1 or nxt == 27:
            if nxt == 27:
                tail.append(nxt)
            break
        tail.append(nxt)
    try:
        win.timeout(delay)
    except curses.error:
        pass
    if len(tail) == 2 and tail[0] in (91, 79) and tail[1] in _ARROW_TAILS:
        want = _ARROW_TAILS[tail[1]]
        mapping = {65: "KEY_UP", 66: "KEY_DOWN", 67: "KEY_RIGHT",
                   68: "KEY_LEFT"}
        resolved = _key_values(mapping[tail[1]])
        return resolved if resolved is not None else want
    for code in reversed(tail):
        try:
            curses.ungetch(code)
        except curses.error:
            pass
    return 27
