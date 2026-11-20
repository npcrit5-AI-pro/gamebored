"""Shared curses UI helpers for GameBored.

Everything here degrades gracefully: small terminals get a friendly
'make the window bigger' message instead of a curses crash, and every
addstr/addch call is guarded against writing past the screen edge.
"""

import curses

MIN_H = 24
MIN_W = 80

TITLE = "GAMEBORED"
QUIT_KEYS = (27, ord("q"), ord("Q"))  # Esc / q


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


def color(num):
    try:
        return curses.color_pair(num)
    except curses.error:
        return 0


def safe_addstr(win, y, x, text, attr=0):
    try:
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
    except curses.error:
        pass


def safe_addch(win, y, x, ch, attr=0):
    try:
        h, w = win.getmaxyx()
        if y < 0 or y >= h or x < 0 or x >= w:
            return
        if y == h - 1 and x == w - 1:
            return
        win.addch(y, x, ch, attr)
    except curses.error:
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
        y = max(0, h // 2 - len(lines) // 2)
        for line in lines:
            x = max(0, (w - len(line)) // 2)
            safe_addstr(win, y, x, line, color(3) | curses.A_BOLD)
            y += 1
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
        up = _key_values("KEY_UP")
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


def game_over_screen(win, game_title, lines, score=None, best=None, is_new_high=False):
    """Show a game-over panel. Returns after any keypress. Returns the key."""
    try:
        win.timeout(-1)
    except curses.error:
        pass
    try:
        h, w = win.getmaxyx()
        box_w = min(w - 4, 52)
        box_lines = []
        box_lines.append("  GAME OVER: %s  " % game_title)
        box_lines.append("")
        for ln in lines:
            box_lines.append(ln)
        if score is not None:
            box_lines.append("")
            box_lines.append("Score: %s" % score)
        if best is not None:
            box_lines.append("Best:  %s" % best)
        if is_new_high:
            box_lines.append("NEW HIGH SCORE!")
        box_lines.append("")
        box_lines.append("Press Enter/q to return to the menu")
        box_h = len(box_lines) + 2
        y0 = max(0, (h - box_h) // 2)
        x0 = max(0, (w - box_w) // 2)
        try:
            win.clear()
        except curses.error:
            pass
        try:
            for i in range(box_h):
                safe_addstr(win, y0 + i, x0, " " * box_w, color(10))
        except curses.error:
            pass
        for i, ln in enumerate(box_lines):
            attr = curses.A_BOLD
            if ln == "NEW HIGH SCORE!":
                attr = curses.A_BOLD | curses.A_BLINK
            centered(win, y0 + 1 + i, ln[:box_w], attr)
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
