"""Tic-Tac-Toe vs the computer (unbeatable minimax, kid-friendly)."""

import curses

from .. import scores as scores_mod
from .. import ui

TITLE = "Tic-Tac-Toe"
DESCRIPTION = "Beat the computer at X/O"
CONTROLS = "Arrows move | Space/Enter place | 1-9 quick place | q/Esc quit"
GAME_ID = "tictactoe"

LINES = (
    (0, 1, 2), (3, 4, 5), (6, 7, 8),
    (0, 3, 6), (1, 4, 7), (2, 5, 8),
    (0, 4, 8), (2, 4, 6),
)


def winner(board):
    for a, b, c in LINES:
        if board[a] and board[a] == board[b] == board[c]:
            return board[a]
    if all(board):
        return "draw"
    return None


def best_move(board, ai="O", human="X"):
    best_score = -10**9
    move = None
    for i in range(9):
        if not board[i]:
            board[i] = ai
            s = _minimax(board, False, ai, human, 0)
            board[i] = ""
            if s > best_score:
                best_score = s
                move = i
    return move


def _minimax(board, is_max, ai, human, depth):
    w = winner(board)
    if w == ai:
        return 10 - depth
    if w == human:
        return depth - 10
    if w == "draw":
        return 0
    if is_max:
        best = -10**9
        for i in range(9):
            if not board[i]:
                board[i] = ai
                best = max(best, _minimax(board, False, ai, human, depth + 1))
                board[i] = ""
        return best
    best = 10**9
    for i in range(9):
        if not board[i]:
            board[i] = human
            best = min(best, _minimax(board, True, ai, human, depth + 1))
            board[i] = ""
    return best


class TicState:
    def __init__(self):
        self.board = [""] * 9
        self.cursor = 4
        self.message = "You are X. Good luck!"

    def human(self, i):
        if self.board[i] or winner(self.board):
            return False
        self.board[i] = "X"
        w = winner(self.board)
        if w:
            self.message = _end_message(w)
            return True
        ai = best_move(self.board)
        if ai is not None:
            self.board[ai] = "O"
        w = winner(self.board)
        self.message = _end_message(w) if w else "Your move!"
        return True


def _end_message(w):
    if w == "X":
        return "You win! Amazing!"
    if w == "O":
        return "Computer wins. Try again!"
    return "It's a draw!"


def draw(screen, st):
    h, w = screen.getmaxyx()
    ui.centered(screen, h // 2 - 7, "TIC-TAC-TOE (you are X)",
                ui.color(1) | curses.A_BOLD)
    ui.centered(screen, h // 2 - 6, st.message, ui.color(3))
    base = h // 2 - 4
    _, sw = screen.getmaxyx()
    ox = max(0, (sw - 13) // 2)
    for r in range(3):
        y = base + r * 2
        cells = []
        for c in range(3):
            i = r * 3 + c
            v = st.board[i] if st.board[i] else str(i + 1)
            if i == st.cursor:
                cells.append("[%s]" % v)
            else:
                cells.append(" %s " % v)
        line = "|".join(cells)
        attr = 0
        ui.safe_addstr(screen, y, ox, line, attr)
        for c in range(3):
            i = r * 3 + c
            v = st.board[i]
            if v:
                a = (ui.color(2) if v == "X" else ui.color(5)) | curses.A_BOLD
                ui.safe_addstr(screen, y, ox + c * 4 + 1, v, a)
                if i == st.cursor:
                    ui.safe_addch(screen, y, ox + c * 4, ord("["),
                                  curses.A_REVERSE)
                    ui.safe_addch(screen, y, ox + c * 4 + 2, ord("]"),
                                  curses.A_REVERSE)
        if r < 2:
            ui.safe_addstr(screen, y + 1, ox, "---+---+---")


def play(stdscr, score_store):
    curses.curs_set(0)
    try:
        stdscr.keypad(True)
        stdscr.timeout(-1)
    except curses.error:
        pass
    st = TicState()
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
        ui.footer(stdscr, CONTROLS)
        try:
            stdscr.refresh()
        except curses.error:
            pass
        w = winner(st.board)
        if w:
            won = w == "X"
            score = 100 if won else (10 if w == "draw" else 0)
            entry = scores_mod.get_entry(score_store, GAME_ID)
            _, is_high = scores_mod.record_play(score_store, GAME_ID, score,
                                                won=won)
            scores_mod.save(score_store)
            ui.game_over_screen(
                stdscr, TITLE, [_end_message(w)],
                score=score, best=max(entry["high"], score),
                is_new_high=is_high, game_id=GAME_ID)
            return
        try:
            key = stdscr.getch()
        except curses.error:
            key = -1
        if key in ui.QUIT_KEYS:
            return
        elif key == curses.KEY_UP:
            st.cursor = (st.cursor - 3) % 9
        elif key == curses.KEY_DOWN:
            st.cursor = (st.cursor + 3) % 9
        elif key == curses.KEY_LEFT:
            st.cursor = (st.cursor - 1) % 9
        elif key == curses.KEY_RIGHT:
            st.cursor = (st.cursor + 1) % 9
        elif key in (ord(" "), 10, 13, curses.KEY_ENTER):
            st.human(st.cursor)
        elif ord("1") <= key <= ord("9"):
            st.human(key - ord("1"))
