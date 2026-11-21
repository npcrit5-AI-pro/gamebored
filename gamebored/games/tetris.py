"""Tetris-style falling blocks."""

import curses
import random
import time

from .. import scores as scores_mod
from .. import ui

TITLE = "Block Stack"
DESCRIPTION = "Tetris-style falling blocks"
CONTROLS = "Left/Right move | Down soft-drop | Up rotate | Space hard-drop | p pause | ? help | q menu"
GAME_ID = "tetris"
CATEGORY = "PUZZLE"

W, H = 10, 20

SHAPES = {
    "I": [(0, 1), (1, 1), (2, 1), (3, 1)],
    "O": [(0, 0), (1, 0), (0, 1), (1, 1)],
    "T": [(1, 0), (0, 1), (1, 1), (2, 1)],
    "S": [(1, 0), (2, 0), (0, 1), (1, 1)],
    "Z": [(0, 0), (1, 0), (1, 1), (2, 1)],
    "J": [(0, 0), (0, 1), (1, 1), (2, 1)],
    "L": [(2, 0), (0, 1), (1, 1), (2, 1)],
}
NAMES = list(SHAPES.keys())
COLORS = {"I": 1, "O": 3, "T": 4, "S": 2, "Z": 5, "J": 6, "L": 3}


def rotate(cells):
    return [(y, -x) for x, y in cells]


def normalized(cells):
    minx = min(x for x, _ in cells)
    miny = min(y for _, y in cells)
    return sorted((x - minx, y - miny) for x, y in cells)


def collides(board, cells, px, py):
    for x, y in cells:
        bx, by = px + x, py + y
        if bx < 0 or bx >= W or by >= H:
            return True
        if by >= 0 and board[by][bx]:
            return True
    return False


def clear_lines_count(board):
    """Remove full rows in place; return number cleared."""
    full = [i for i, row in enumerate(board) if all(row)]
    for i in full:
        del board[i]
        board.insert(0, [None] * W)
    return len(full)


class TetrisState:
    def __init__(self, seed=None):
        self.rng = random.Random(seed)
        self.board = [[None] * W for _ in range(H)]
        self.score = 0
        self.lines = 0
        self.level = 1
        self.over = False
        self.bag = []
        self.piece = None
        self.px = self.py = 0
        self.spawn()

    def _next_shape(self):
        if not self.bag:
            self.bag = NAMES[:]
            self.rng.shuffle(self.bag)
        return self.bag.pop()

    def spawn(self):
        name = self._next_shape()
        self.piece = (name, normalized(SHAPES[name]))
        self.px, self.py = 3, 0
        if collides(self.board, self.piece[1], self.px, self.py):
            self.over = True

    def move(self, dx, dy):
        if self.over or self.piece is None:
            return False
        try:
            dx, dy = int(dx), int(dy)
        except (TypeError, ValueError):
            return False
        name, cells = self.piece
        if not collides(self.board, cells, self.px + dx, self.py + dy):
            self.px += dx
            self.py += dy
            return True
        return False

    def rotate_piece(self):
        if self.over or self.piece is None:
            return
        name, cells = self.piece
        if name == "O":
            return
        nc = normalized(rotate(cells))
        for dx, dy in ((0, 0), (-1, 0), (1, 0), (0, -1), (-2, 0), (2, 0)):
            if not collides(self.board, nc, self.px + dx, self.py + dy):
                self.piece = (name, nc)
                self.px += dx
                self.py += dy
                return

    def lock(self):
        name, cells = self.piece
        for x, y in cells:
            bx, by = self.px + x, self.py + y
            if by >= 0:
                self.board[by][bx] = name
        n = clear_lines_count(self.board)
        self.lines += n
        self.score += [0, 40, 100, 300, 1200][min(n, 4)] * self.level
        self.level = 1 + self.lines // 10
        self.spawn()

    def gravity(self):
        if not self.move(0, 1):
            self.lock()

    def hard_drop(self):
        while self.move(0, 1):
            pass
        self.lock()
        self.score += 2


def draw(screen, st):
    h, w = screen.getmaxyx()
    ox = max(0, (w - W * 2 - 2) // 2)
    oy = max(1, (h - H) // 2)
    cells = {(x + st.px, y + st.py): st.piece[0] for x, y in st.piece[1]} if st.piece else {}
    for y in range(H):
        ui.safe_addch(screen, oy + y, ox, ord("|"))
        ui.safe_addch(screen, oy + y, ox + W * 2 + 1, ord("|"))
        for x in range(W):
            name = cells.get((x, y), st.board[y][x])
            if name:
                ui.safe_addstr(screen, oy + y, ox + 1 + x * 2, "[]",
                               ui.color(COLORS.get(name, 2)) | curses.A_BOLD)
            else:
                ui.safe_addstr(screen, oy + y, ox + 1 + x * 2, " .")
    ui.safe_addstr(screen, oy + H, ox, "+" + "-" * (W * 2) + "+")
    info_x = ox + W * 2 + 4
    if info_x + 16 < w:
        ui.safe_addstr(screen, oy, info_x, "BLOCK STACK", ui.color(1) | curses.A_BOLD)
        ui.safe_addstr(screen, oy + 2, info_x, "Score %d" % st.score)
        ui.safe_addstr(screen, oy + 3, info_x, "Lines %d" % st.lines)
        ui.safe_addstr(screen, oy + 4, info_x, "Level %d" % st.level)
    ui.centered(screen, 0, "BLOCK STACK  score %d  lines %d" % (st.score, st.lines),
                ui.color(4) | curses.A_BOLD)


def play(stdscr, score_store):
    curses.curs_set(0)
    try:
        stdscr.keypad(True)
    except curses.error:
        pass
    st = TetrisState()
    try:
        stdscr.timeout(50)
    except curses.error:
        pass
    last = time.time()
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
            key = stdscr.getch()
        except curses.error:
            key = -1
        if key in ui.QUIT_KEYS:
            scores_mod.record_play(score_store, GAME_ID, st.score)
            scores_mod.save(score_store)
            return
        elif key in ui.PAUSE_KEYS:
            if ui.pause_overlay(stdscr) == "quit":
                return
            try:
                stdscr.timeout(50)
            except curses.error:
                pass
            last = time.time()
            continue
        if key in ui.HELP_KEYS:
            ui.show_help_overlay(stdscr, TITLE, CONTROLS)
            try:
                stdscr.timeout(50)
            except curses.error:
                pass
            last = time.time()
            continue
        if key == curses.KEY_RESIZE:
            continue
        elif key == curses.KEY_LEFT:
            st.move(-1, 0)
        elif key == curses.KEY_RIGHT:
            st.move(1, 0)
        elif key == curses.KEY_DOWN:
            st.move(0, 1)
            st.score += 1
        elif key == curses.KEY_UP:
            st.rotate_piece()
        elif key == ord(" "):
            st.hard_drop()
        interval = max(0.08, 0.55 - (st.level - 1) * 0.05)
        if time.time() - last > interval:
            last = time.time()
            st.gravity()
            if st.over:
                entry = scores_mod.get_entry(score_store, GAME_ID)
                _, is_high = scores_mod.record_play(score_store, GAME_ID, st.score)
                scores_mod.save(score_store)
                ui.game_over_screen(
                    stdscr, TITLE,
                    ["The stack reached the top!",
                     "Lines cleared: %d" % st.lines],
                    score=st.score, best=max(entry["high"], st.score),
                    is_new_high=is_high, game_id=GAME_ID, won=False)
                return
        try:
            stdscr.clear()
        except curses.error:
            pass
        draw(stdscr, st)
        ui.game_footer(stdscr, CONTROLS)
        try:
            stdscr.refresh()
        except curses.error:
            pass
