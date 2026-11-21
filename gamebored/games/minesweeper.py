"""Minesweeper: clear the field without hitting a mine."""

import curses
import random
import time

from .. import scores as scores_mod
from .. import ui

TITLE = "Minesweeper"
DESCRIPTION = "Clear mines without boom"
CONTROLS = "Arrows move | Space/Enter dig | f flag | p pause | q menu"
GAME_ID = "minesweeper"
CATEGORY = "PUZZLE"

ROWS, COLS, MINES = 9, 9, 10


def neighbors(r, c):
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            if dr == 0 and dc == 0:
                continue
            yield r + dr, c + dc


class MineState:
    def __init__(self, rows=ROWS, cols=COLS, mines=MINES, seed=None,
                 safe=None, preset=None):
        self.rows, self.cols, self.mines_total = rows, cols, mines
        self.rng = random.Random(seed)
        self.mines = set()
        self.revealed = [[False] * cols for _ in range(rows)]
        self.flagged = [[False] * cols for _ in range(rows)]
        self.counts = [[0] * cols for _ in range(rows)]
        self.started = False
        self.over = False
        self.won = False
        self.boom = None
        self.start_time = time.time()
        self.elapsed = 0
        if preset is not None:
            self.mines = set(preset)
            self.started = True
            self._compute_counts()

    def _compute_counts(self):
        for r in range(self.rows):
            for c in range(self.cols):
                n = 0
                for nr, nc in neighbors(r, c):
                    if 0 <= nr < self.rows and 0 <= nc < self.cols:
                        if (nr, nc) in self.mines:
                            n += 1
                self.counts[r][c] = n

    def _place(self, safe):
        cells = [(r, c) for r in range(self.rows) for c in range(self.cols)
                 if (r, c) != safe]
        self.rng.shuffle(cells)
        self.mines = set(cells[: self.mines_total])
        self.started = True
        self._compute_counts()

    def _in_bounds(self, r, c):
        return 0 <= r < self.rows and 0 <= c < self.cols

    def reveal(self, r, c):
        if not self._in_bounds(r, c):
            return
        if self.over or self.flagged[r][c] or self.revealed[r][c]:
            return
        if not self.started:
            self._place((r, c))
        if (r, c) in self.mines:
            self.revealed[r][c] = True
            self.over = True
            self.won = False
            self.boom = (r, c)
            self.elapsed = time.time() - self.start_time
            return
        stack = [(r, c)]
        while stack:
            cr, cc = stack.pop()
            if self.revealed[cr][cc] or self.flagged[cr][cc]:
                continue
            self.revealed[cr][cc] = True
            if self.counts[cr][cc] == 0:
                for nr, nc in neighbors(cr, cc):
                    if 0 <= nr < self.rows and 0 <= nc < self.cols:
                        if not self.revealed[nr][nc] and (nr, nc) not in self.mines:
                            stack.append((nr, nc))
        if self.check_win():
            self.over = True
            self.won = True
            self.elapsed = time.time() - self.start_time

    def toggle_flag(self, r, c):
        if not self._in_bounds(r, c):
            return
        if self.over or self.revealed[r][c]:
            return
        self.flagged[r][c] = not self.flagged[r][c]

    def check_win(self):
        for r in range(self.rows):
            for c in range(self.cols):
                if (r, c) not in self.mines and not self.revealed[r][c]:
                    return False
        return True

    def flags_used(self):
        return sum(1 for r in range(self.rows) for c in range(self.cols)
                   if self.flagged[r][c])


def draw(screen, st, cur):
    h, w = screen.getmaxyx()
    cw = 3
    ox = max(0, (w - COLS * cw) // 2)
    oy = max(2, (h - ROWS) // 2)
    ui.centered(screen, 0, "MINESWEEPER  mines: %d  flags: %d/%d" % (
        MINES, st.flags_used(), MINES), ui.color(5) | curses.A_BOLD)
    for r in range(ROWS):
        for c in range(COLS):
            x = ox + c * cw
            y = oy + r
            attr = curses.A_REVERSE if (r, c) == cur else 0
            if st.over and (r, c) in st.mines and (r, c) == st.boom:
                ui.safe_addstr(screen, y, x, "[X]", attr | ui.color(5) | curses.A_BOLD)
            elif st.revealed[r][c]:
                if (r, c) in st.mines:
                    ui.safe_addstr(screen, y, x, "[*]", attr | ui.color(5))
                else:
                    n = st.counts[r][c]
                    label = "[%s]" % (str(n) if n else " ")
                    a = attr
                    if n:
                        a |= ui.color((n % 6) + 1)
                    ui.safe_addstr(screen, y, x, label, a)
            elif st.flagged[r][c]:
                ui.safe_addstr(screen, y, x, "[F]", attr | ui.color(3) | curses.A_BOLD)
            else:
                ui.safe_addstr(screen, y, x, "[ ]", attr)


def play(stdscr, score_store):
    curses.curs_set(0)
    try:
        stdscr.keypad(True)
    except curses.error:
        pass
    try:
        stdscr.timeout(-1)
    except curses.error:
        pass
    st = MineState()
    cur = [0, 0]
    while True:
        if ui.too_small(stdscr):
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
        except curses.error:
            pass
        draw(stdscr, st, tuple(cur))
        ui.game_footer(stdscr, CONTROLS)
        try:
            stdscr.refresh()
        except curses.error:
            pass
        if st.over:
            score = max(0, 1000 - int(st.elapsed) * 5) if st.won else 0
            if st.won:
                score += 500
            entry = scores_mod.get_entry(score_store, GAME_ID)
            _, is_high = scores_mod.record_play(
                score_store, GAME_ID, score, won=st.won)
            scores_mod.save(score_store)
            ui.game_over_screen(
                stdscr, TITLE,
                ["You cleared every mine! Time: %ds" % int(st.elapsed)
                 if st.won else "BOOM! You hit a mine."],
                won=st.won,
                score=score, best=max(entry["high"], score),
                is_new_high=is_high, game_id=GAME_ID)
            return
        try:
            key = stdscr.getch()
        except curses.error:
            key = -1
        if key in ui.QUIT_KEYS:
            return
        elif key in ui.PAUSE_KEYS:
            if ui.pause_overlay(stdscr) == "quit":
                return
            continue
        if key in ui.HELP_KEYS:
            ui.show_help_overlay(stdscr, TITLE, CONTROLS)
            continue
        if key == curses.KEY_RESIZE:
            continue
        elif key == curses.KEY_UP:
            cur[0] = (cur[0] - 1) % ROWS
        elif key == curses.KEY_DOWN:
            cur[0] = (cur[0] + 1) % ROWS
        elif key == curses.KEY_LEFT:
            cur[1] = (cur[1] - 1) % COLS
        elif key == curses.KEY_RIGHT:
            cur[1] = (cur[1] + 1) % COLS
        elif key in (ord(" "), 10, 13, curses.KEY_ENTER):
            st.reveal(cur[0], cur[1])
        elif key in (ord("f"), ord("F")):
            st.toggle_flag(cur[0], cur[1])
