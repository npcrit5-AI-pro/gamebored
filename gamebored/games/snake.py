"""Snake: eat food, grow, don't hit walls or yourself."""

import curses
import random
import time

from .. import scores as scores_mod
from .. import ui

TITLE = "Snake"
DESCRIPTION = "Eat, grow, don't crash!"
CONTROLS = "Arrows/WASD move | q/Esc quit"
GAME_ID = "snake"

UP, DOWN, LEFT, RIGHT = (0, -1), (0, 1), (-1, 0), (1, 0)


class SnakeState:
    def __init__(self, width=20, height=20, seed=None):
        self.width = width
        self.height = height
        self.rng = random.Random(seed)
        cx, cy = width // 2, height // 2
        self.snake = [(cx, cy), (cx - 1, cy), (cx - 2, cy)]
        self.direction = RIGHT
        self.pending = RIGHT
        self.alive = True
        self.score = 0
        self.food = None
        self._place_food()

    def _place_food(self):
        free = [(x, y) for y in range(self.height) for x in range(self.width)
                if (x, y) not in self.snake]
        self.food = self.rng.choice(free) if free else None

    def set_direction(self, d):
        dx, dy = d
        pdx, pdy = self.pending
        if (dx, dy) != (-pdx, -pdy):
            self.pending = d

    def step(self):
        if not self.alive:
            return False
        self.direction = self.pending
        dx, dy = self.direction
        hx, hy = self.snake[0]
        nx, ny = hx + dx, hy + dy
        if nx < 0 or ny < 0 or nx >= self.width or ny >= self.height:
            self.alive = False
            return False
        growing = self.food is not None and (nx, ny) == self.food
        body = self.snake if growing else self.snake[:-1]
        if (nx, ny) in body:
            self.alive = False
            return False
        self.snake.insert(0, (nx, ny))
        if growing:
            self.score += 1
            self._place_food()
            if self.food is None:
                self.alive = False  # filled the board: you win!
        else:
            self.snake.pop()
        return True


def new_state(width=20, height=20, seed=None):
    return SnakeState(width, height, seed)


def draw(screen, st):
    h, w = screen.getmaxyx()
    bw, bh = st.width, st.height
    ox = max(0, (w - bw * 2) // 2)
    oy = max(1, (h - bh) // 2)
    for y in range(bh):
        for x in range(bw):
            ch = "  "
            attr = 0
            if st.food == (x, y):
                ch = "()"
                attr = ui.color(5) | curses.A_BOLD
            elif (x, y) == st.snake[0]:
                ch = "OO"
                attr = ui.color(2) | curses.A_BOLD
            elif (x, y) in st.snake:
                ch = "oo"
                attr = ui.color(2)
            else:
                ch = " ."
                attr = 0
            ui.safe_addstr(screen, oy + y, ox + x * 2, ch, attr)
    # border
    for y in range(bh):
        ui.safe_addch(screen, oy + y, ox - 1, ord("|"))
        ui.safe_addch(screen, oy + y, ox + bw * 2, ord("|"))
    for x in range(-1, bw * 2 + 1):
        ui.safe_addch(screen, oy - 1, ox + x, ord("-"))
        ui.safe_addch(screen, oy + bh, ox + x, ord("-"))
    ui.centered(screen, 0, "SNAKE  score: %d" % st.score,
                ui.color(2) | curses.A_BOLD)


KEYMAP = {
    curses.KEY_UP: UP, curses.KEY_DOWN: DOWN,
    curses.KEY_LEFT: LEFT, curses.KEY_RIGHT: RIGHT,
    ord("w"): UP, ord("s"): DOWN, ord("a"): LEFT, ord("d"): RIGHT,
    ord("W"): UP, ord("S"): DOWN, ord("A"): LEFT, ord("D"): RIGHT,
}


def play(stdscr, score_store):
    curses.curs_set(0)
    try:
        stdscr.keypad(True)
    except curses.error:
        pass
    h, w = stdscr.getmaxyx()
    bw = min(30, max(10, (w - 6) // 2))
    bh = min(20, max(8, h - 6))
    st = SnakeState(bw, bh)
    delay = 0.12
    last = time.time()
    try:
        stdscr.timeout(50)
    except curses.error:
        pass
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
            entry, _ = scores_mod.record_play(score_store, GAME_ID, st.score)
            scores_mod.save(score_store)
            return
        if key in KEYMAP:
            st.set_direction(KEYMAP[key])
        now = time.time()
        speed = max(0.05, delay - st.score * 0.002)
        if now - last >= speed:
            last = now
            st.step()
            if not st.alive:
                entry = scores_mod.get_entry(score_store, GAME_ID)
                _, is_high = scores_mod.record_play(
                    score_store, GAME_ID, st.score)
                scores_mod.save(score_store)
                best = max(entry["high"], st.score)
                won = st.food is None
                ui.game_over_screen(
                    stdscr, TITLE,
                    ["You %s!" % ("filled the board, champion" if won else "crashed"),
                     "Length: %d" % (len(st.snake))],
                    score=st.score, best=best, is_new_high=is_high,
                    game_id=GAME_ID)
                return
        try:
            stdscr.clear()
        except curses.error:
            pass
        draw(stdscr, st)
        ui.footer(stdscr, "%s | length %d" % (CONTROLS, len(st.snake)))
        try:
            stdscr.refresh()
        except curses.error:
            pass
