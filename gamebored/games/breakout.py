"""Breakout: bounce the ball, smash every brick."""

import curses
import time

from .. import scores as scores_mod
from .. import ui

TITLE = "Breakout"
DESCRIPTION = "Bounce ball, smash bricks"
CONTROLS = "Left/Right or A/D move paddle | 3 lives | p pause | q menu"
GAME_ID = "breakout"
CATEGORY = "ACTION"

BRICK_ROWS, BRICK_COLS = 5, 10


class BreakState:
    def __init__(self, width=50, height=18):
        self.width = width
        self.height = height
        self.paddle = width // 2
        self.paddle_w = 7
        self.reset_ball()
        self.lives = 3
        self.score = 0
        self.over = False
        self.won = False
        self.bricks = set()
        for r in range(BRICK_ROWS):
            for c in range(BRICK_COLS):
                self.bricks.add((c, r))

    def reset_ball(self):
        self.bx = self.width // 2
        self.by = self.height - 4
        self.vx = 1.0
        self.vy = -1.0

    def step(self, move=0):
        try:
            move = int(move)
        except (TypeError, ValueError):
            move = 0
        self.paddle = max(self.paddle_w // 2,
                          min(self.width - self.paddle_w // 2 - 1,
                              self.paddle + move))
        self.bx += self.vx
        self.by += self.vy
        if self.bx <= 0:
            self.bx = 0
            self.vx = abs(self.vx)
        elif self.bx >= self.width - 1:
            self.bx = self.width - 1
            self.vx = -abs(self.vx)
        if self.by <= 0:
            self.by = 0
            self.vy = abs(self.vy)
        # brick collision (map ball to brick grid)
        top = 2
        bw = max(1, self.width // BRICK_COLS)
        bc = int(self.bx // bw)
        br = int(self.by - top)
        if (bc, br) in self.bricks:
            self.bricks.discard((bc, br))
            self.score += 10
            self.vy = abs(self.vy) if self.vy < 0 else self.vy
            self.vy = -self.vy if self.vy != 0 else 1.0
            if not self.bricks:
                self.over = True
                self.won = True
                return
        # paddle
        if self.vy > 0 and int(round(self.by)) >= self.height - 3:
            if abs(self.bx - self.paddle) <= self.paddle_w // 2:
                self.by = self.height - 3
                self.vy = -abs(self.vy)
                self.vx += (self.bx - self.paddle) * 0.15
                self.vx = max(-2.0, min(2.0, self.vx))
            elif self.by >= self.height - 1:
                self.lives -= 1
                if self.lives <= 0:
                    self.over = True
                    self.won = False
                else:
                    self.reset_ball()


def draw(screen, st, ox, oy):
    bw = max(1, st.width // BRICK_COLS)
    for y in range(st.height):
        for x in range(st.width):
            ui.safe_addch(screen, oy + y, ox + x, ord(" "))
    for (bc, br) in st.bricks:
        attr = ui.color((br % 6) + 1) | curses.A_BOLD
        for i in range(bw - 1):
            ui.safe_addch(screen, oy + 2 + br, ox + bc * bw + i, ord("#"), attr)
    for i in range(-st.paddle_w // 2, st.paddle_w // 2 + 1):
        ui.safe_addch(screen, oy + st.height - 2, ox + st.paddle + i, ord("="),
                      ui.color(1) | curses.A_BOLD)
    ui.safe_addch(screen, oy + int(round(st.by)), ox + int(round(st.bx)),
                  ord("O"), ui.color(3) | curses.A_BOLD)
    ui.centered(screen, 0, "BREAKOUT  score %d  lives %d  bricks %d" % (
        st.score, st.lives, len(st.bricks)), ui.color(4) | curses.A_BOLD)


def play(stdscr, score_store):
    curses.curs_set(0)
    try:
        stdscr.keypad(True)
        stdscr.timeout(50)
    except curses.error:
        pass
    h, w = stdscr.getmaxyx()
    fw = min(56, max(30, w - 4))
    fh = min(18, max(12, h - 5))
    st = BreakState(fw, fh)
    move = 0
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
            scores_mod.record_play(score_store, GAME_ID, st.score,
                                   won=st.won)
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
        elif key in (curses.KEY_LEFT, ord("a"), ord("A")):
            move = -2
        elif key in (curses.KEY_RIGHT, ord("d"), ord("D")):
            move = 2
        if time.time() - last > 0.07:
            last = time.time()
            st.step(move)
            move = 0
            if st.over:
                score = st.score + (200 if st.won else 0)
                entry = scores_mod.get_entry(score_store, GAME_ID)
                _, is_high = scores_mod.record_play(score_store, GAME_ID,
                                                    score, won=st.won)
                scores_mod.save(score_store)
                ui.game_over_screen(
                    stdscr, TITLE,
                    ["You smashed every brick!" if st.won
                     else "Out of lives!"],
                    score=score, best=max(entry["high"], score),
                    is_new_high=is_high, game_id=GAME_ID, won=st.won)
                return
        try:
            stdscr.clear()
        except curses.error:
            pass
        h2, w2 = stdscr.getmaxyx()
        ox = max(0, (w2 - st.width) // 2)
        oy = max(2, (h2 - st.height) // 2)
        draw(stdscr, st, ox, oy)
        ui.game_footer(stdscr, CONTROLS)
        try:
            stdscr.refresh()
        except curses.error:
            pass
