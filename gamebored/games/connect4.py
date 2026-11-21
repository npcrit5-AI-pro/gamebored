"""Connect Four vs the computer: drop discs, line up four.

You are X, the computer is O. Pick a column (Left/Right + Space, or 1-7)
and your disc falls to the lowest free cell. First to connect four
horizontally, vertically, or diagonally wins. Win = 150, draw = 25.
"""

import curses
import random

from .. import scores as scores_mod
from .. import ui

TITLE = "Connect Four"
DESCRIPTION = "Line up four vs the CPU"
CONTROLS = "Left/Right move | Space/Enter or 1-7 drop | p pause | ? help | q menu"
GAME_ID = "connect4"
CATEGORY = "CLASSIC"

ROWS, COLS = 6, 7
WIN_SCORE, DRAW_SCORE = 150, 25


class ConnectState:
    """Headless Connect Four logic: no curses calls in here."""

    def __init__(self, seed=None):
        self.rng = random.Random(seed)
        self.board = [""] * (ROWS * COLS)  # "" / "X" / "O"
        self.cursor = COLS // 2
        self.over = False
        self.winner_mark = None

    def cell(self, r, c):
        if not isinstance(r, int) or not isinstance(c, int):
            return ""
        if not 0 <= r < ROWS or not 0 <= c < COLS:
            return ""
        return self.board[r * COLS + c]

    def drop(self, col, mark):
        """Drop mark into col; returns the row or None if full/invalid."""
        if not isinstance(col, int):
            return None
        if not 0 <= col < COLS:
            return None
        for r in range(ROWS - 1, -1, -1):
            if self.cell(r, col) == "":
                self.board[r * COLS + col] = mark
                return r
        return None

    def full(self):
        return all(c != "" for c in self.board)

    @staticmethod
    def check(board):
        for r in range(ROWS):
            for c in range(COLS):
                mark = board[r * COLS + c]
                if not mark:
                    continue
                for dr, dc in ((0, 1), (1, 0), (1, 1), (1, -1)):
                    cells = [(r + dr * k, c + dc * k) for k in range(4)]
                    if all(0 <= rr < ROWS and 0 <= cc < COLS and
                           board[rr * COLS + cc] == mark for rr, cc in cells):
                        return mark
        if all(c != "" for c in board):
            return "draw"
        return None

    def result(self):
        return self.check(self.board)

    def ai_move(self):
        """Simple CPU: win if it can, block if it must, else near-center."""
        # winning move
        for c in range(COLS):
            trial = self.board[:]
            if _drop_on(trial, c, "O") and self.check(trial) == "O":
                self.drop(c, "O")
                return c
        # block the player's win
        for c in range(COLS):
            trial = self.board[:]
            if _drop_on(trial, c, "X") and self.check(trial) == "X":
                self.drop(c, "O")
                return c
        order = [3, 2, 4, 1, 5, 0, 6]
        free = [c for c in order if self.cell(0, c) == ""]
        if not free:
            return None
        choice = self.rng.choice(free[:3])
        self.drop(choice, "O")
        return choice


def _drop_on(board, col, mark):
    for r in range(ROWS - 1, -1, -1):
        if board[r * COLS + col] == "":
            board[r * COLS + col] = mark
            return True
    return False


def new_state(seed=None):
    return ConnectState(seed)


def draw(screen, st):
    h, w = screen.getmaxyx()
    ui.centered(screen, 1, "CONNECT FOUR  you=X cpu=O",
                ui.color(4) | curses.A_BOLD)
    y0 = 3
    total_w = COLS * 4
    x0 = max(0, (w - total_w) // 2)
    for c in range(COLS):
        marker = " v " if c == st.cursor else "   "
        ui.safe_addstr(screen, y0, x0 + c * 4, marker,
                       ui.color(2) | curses.A_BOLD)
    for r in range(ROWS):
        for c in range(COLS):
            mark = st.cell(r, c)
            if mark == "X":
                ch, attr = "X", ui.color(2) | curses.A_BOLD
            elif mark == "O":
                ch, attr = "O", ui.color(5) | curses.A_BOLD
            else:
                ch, attr = ".", 0
            ui.safe_addstr(screen, y0 + 1 + r, x0 + c * 4, "[%s]" % ch, attr)


def play(stdscr, score_store):
    curses.curs_set(0)
    try:
        stdscr.keypad(True)
        stdscr.timeout(-1)
    except curses.error:
        pass
    st = ConnectState()
    message = "Your move!"
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
        ui.centered(stdscr, 3 + ROWS + 2, message, ui.color(3))
        ui.game_footer(stdscr, CONTROLS)
        try:
            stdscr.refresh()
        except curses.error:
            pass
        result = st.result()
        if result:
            won = result == "X"
            score = WIN_SCORE if won else (DRAW_SCORE if result == "draw"
                                          else 0)
            entry = scores_mod.get_entry(score_store, GAME_ID)
            _, is_high = scores_mod.record_play(score_store, GAME_ID, score,
                                                won=won)
            scores_mod.save(score_store)
            if result == "draw":
                end = "Board full: a draw!"
            elif won:
                end = "Four in a row: you win!"
            else:
                end = "The CPU connected four. Rematch?"
            ui.game_over_screen(stdscr, TITLE, [end], score=score,
                                best=max(entry["high"], score),
                                is_new_high=is_high, game_id=GAME_ID, won=won)
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
        elif key == curses.KEY_LEFT:
            st.cursor = (st.cursor - 1) % COLS
        elif key == curses.KEY_RIGHT:
            st.cursor = (st.cursor + 1) % COLS
        elif key in (10, 13, curses.KEY_ENTER, ord(" ")):
            col = st.cursor
            if st.drop(col, "X") is None:
                message = "Column full: pick another!"
                continue
            if not st.result():
                st.ai_move()
            message = "Your move!"
        elif ord("1") <= key <= ord("7"):
            col = key - ord("1")
            if st.drop(col, "X") is None:
                message = "Column full: pick another!"
                continue
            if not st.result():
                st.ai_move()
            message = "Your move!"
