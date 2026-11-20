"""2048: slide tiles, merge to 2048."""

import curses
import random

from .. import scores as scores_mod
from .. import ui

TITLE = "2048"
DESCRIPTION = "Slide and merge to 2048"
CONTROLS = "Arrows/WASD slide | r restart | p pause | ? help | q menu"
GAME_ID = "g2048"
CATEGORY = "PUZZLE"
SIZE = 4


def empty_board():
    return [[0] * SIZE for _ in range(SIZE)]


def _slide_row_left(row):
    tiles = [v for v in row if v]
    out = []
    gained = 0
    i = 0
    while i < len(tiles):
        if i + 1 < len(tiles) and tiles[i] == tiles[i + 1]:
            v = tiles[i] * 2
            out.append(v)
            gained += v
            i += 2
        else:
            out.append(tiles[i])
            i += 1
    out += [0] * (SIZE - len(out))
    return out, gained


def move_left(board):
    moved = False
    gained = 0
    new = []
    for row in board:
        nr, g = _slide_row_left(row)
        gained += g
        if nr != row:
            moved = True
        new.append(nr)
    return new, gained, moved


def _reverse(board):
    return [row[::-1] for row in board]


def _transpose(board):
    return [list(r) for r in zip(*board)]


def move_board(board, direction):
    """direction in {'left','right','up','down'}. Returns (new, gained, moved)."""
    if direction == "left":
        return move_left(board)
    if direction == "right":
        rev, g, m = move_left(_reverse(board))
        return _reverse(rev), g, m
    if direction == "up":
        tr, g, m = move_left(_transpose(board))
        return _transpose(tr), g, m
    if direction == "down":
        tr = _transpose(board)
        rev, g, m = move_left(_reverse(tr))
        return _transpose(_reverse(rev)), g, m
    raise ValueError(direction)


def can_move(board):
    for row in board:
        if 0 in row:
            return True
    for y in range(SIZE):
        for x in range(SIZE):
            if x + 1 < SIZE and board[y][x] == board[y][x + 1]:
                return True
            if y + 1 < SIZE and board[y][x] == board[y + 1][x]:
                return True
    return False


class State2048:
    def __init__(self, seed=None):
        self.rng = random.Random(seed)
        self.board = empty_board()
        self.score = 0
        self.over = False
        self.won = False
        self.spawn()
        self.spawn()

    def spawn(self):
        empties = [(y, x) for y in range(SIZE) for x in range(SIZE)
                   if self.board[y][x] == 0]
        if not empties:
            return
        y, x = self.rng.choice(empties)
        self.board[y][x] = 4 if self.rng.random() < 0.1 else 2

    def move(self, direction):
        new, gained, moved = move_board(self.board, direction)
        if moved:
            self.board = new
            self.score += gained
            if any(2048 in row for row in self.board):
                self.won = True
            self.spawn()
            if not can_move(self.board):
                self.over = True
        elif not can_move(self.board):
            self.over = True
        return moved


def draw(screen, st):
    h, w = screen.getmaxyx()
    cw = 7
    ox = max(0, (w - (cw * SIZE + SIZE + 1)) // 2)
    oy = max(2, (h - (SIZE * 2 + 1)) // 2)
    ui.centered(screen, 0, "2048  score: %d" % st.score,
                ui.color(3) | curses.A_BOLD)
    if st.won and not st.over:
        ui.centered(screen, 1, "You made 2048! Keep going!",
                    ui.color(2) | curses.A_BOLD)
    for y in range(SIZE):
        for x in range(SIZE):
            v = st.board[y][x]
            label = str(v) if v else ""
            cell = label.center(cw - 1)
            attr = 0
            if v >= 2048:
                attr = ui.color(10) | curses.A_BOLD
            elif v >= 128:
                attr = ui.color(5) | curses.A_BOLD
            elif v >= 16:
                attr = ui.color(3) | curses.A_BOLD
            elif v:
                attr = ui.color(1)
            ui.safe_addstr(screen, oy + y * 2, ox + x * (cw + 1), "+" + "-" * cw)
            ui.safe_addstr(screen, oy + y * 2 + 1, ox + x * (cw + 1), "|" + cell, attr)
    ui.safe_addstr(screen, oy + SIZE * 2, ox, ("+" + "-" * cw) * SIZE + "+")


KEYS = {
    curses.KEY_UP: "up", curses.KEY_DOWN: "down",
    curses.KEY_LEFT: "left", curses.KEY_RIGHT: "right",
    ord("w"): "up", ord("s"): "down", ord("a"): "left", ord("d"): "right",
    ord("W"): "up", ord("S"): "down", ord("A"): "left", ord("D"): "right",
}


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
    st = State2048()
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
        draw(stdscr, st)
        ui.game_footer(stdscr, CONTROLS)
        try:
            stdscr.refresh()
        except curses.error:
            pass
        if st.over:
            entry = scores_mod.get_entry(score_store, GAME_ID)
            _, is_high = scores_mod.record_play(
                score_store, GAME_ID, st.score, won=st.won)
            scores_mod.save(score_store)
            ui.game_over_screen(
                stdscr, TITLE,
                ["No more moves!" if not st.won else "Amazing run!",
                 "Final board score: %d" % st.score],
                won=st.won,
                score=st.score, best=max(entry["high"], st.score),
                is_new_high=is_high, game_id=GAME_ID)
            return
        try:
            key = stdscr.getch()
        except curses.error:
            key = -1
        if key in ui.QUIT_KEYS:
            scores_mod.record_play(score_store, GAME_ID, st.score, won=st.won)
            scores_mod.save(score_store)
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
        if key in (ord("r"), ord("R")):
            st = State2048()
        elif key in KEYS:
            st.move(KEYS[key])
