"""Flappy: squeeze through as many pipes as you can.

Space (or Up) flaps your wings; gravity does the rest. Each pipe you
thread scores 1 point. Touch a pipe, the floor, or the ceiling and the
flight is over. Your raw score is pipes passed.
"""

import curses
import random
import time

from .. import scores as scores_mod
from .. import ui

TITLE = "Flappy"
DESCRIPTION = "Flap through the pipes!"
CONTROLS = "Space/Up flap | q/Esc quit"
GAME_ID = "flappy"

GRAVITY = 0.35
FLAP_VY = -1.6
GAP = 5


class FlapState:
    """Headless flapping logic: no curses calls in here."""

    def __init__(self, width=40, height=16, seed=None, gap=GAP):
        self.width = width
        self.height = height
        self.gap = gap
        self.rng = random.Random(seed)
        self.bird_x = 8
        self.bird_y = float(height // 2)
        self.vy = 0.0
        self.pipes = []  # [x, gap_center]
        self.score = 0
        self.over = False
        self.ticks = 0
        self._spawn(initial=True)

    def _spawn(self, initial=False):
        x = self.width - 2 if not initial else self.width - 2
        if initial:
            self.pipes = [[x, self.height // 2],
                          [x + 14, self.height // 2]]
        else:
            cy = self.rng.randrange(3, self.height - 3)
            self.pipes.append([x, cy])

    def step(self, flap=False):
        """Advance one tick; returns False when the flight ends."""
        if self.over:
            return False
        self.ticks += 1
        self.vy = FLAP_VY if flap else self.vy + GRAVITY
        self.bird_y += self.vy
        for pipe in self.pipes:
            pipe[0] -= 1
        # score pipes as they pass the bird
        for pipe in self.pipes:
            if pipe[0] == self.bird_x - 1:
                self.score += 1
        # recycle off-screen pipes
        if self.pipes and self.pipes[0][0] < -1:
            self.pipes.pop(0)
            self._spawn()
        # ceiling / floor
        if self.bird_y < 0 or self.bird_y >= self.height:
            self.over = True
            return False
        # pipe collision
        y = int(self.bird_y)
        for px, cy in self.pipes:
            if px == self.bird_x:
                half = self.gap // 2
                if abs(y - cy) > half:
                    self.over = True
                    return False
        return True


def new_state(width=40, height=16, seed=None):
    return FlapState(width, height, seed)


def draw(screen, st):
    h, w = screen.getmaxyx()
    ui.centered(screen, 1, "FLAPPY  pipes:%d" % st.score,
                ui.color(2) | curses.A_BOLD)
    fw, fh = st.width, st.height
    x0 = max(0, (w - fw) // 2)
    y0 = max(2, (h - fh) // 2)
    for py in range(fh):
        for px in range(fw):
            ch, attr = " ", 0
            by = int(st.bird_y)
            if px == st.bird_x and py == by and not st.over:
                ch, attr = "@", ui.color(3) | curses.A_BOLD
            else:
                for qx, cy in st.pipes:
                    if px == qx:
                        half = st.gap // 2
                        if abs(py - cy) > half:
                            ch, attr = "#", ui.color(2)
                            break
            if ch != " ":
                ui.safe_addch(screen, y0 + py, x0 + px, ord(ch), attr)
    # borders
    for px in range(fw):
        ui.safe_addch(screen, y0 - 1, x0 + px, ord("-"))
        ui.safe_addch(screen, y0 + fh, x0 + px, ord("-"))


def play(stdscr, score_store):
    curses.curs_set(0)
    try:
        stdscr.keypad(True)
        stdscr.timeout(80)
    except curses.error:
        pass
    fw = min(44, max(24, 40))
    fh = min(16, max(10, 14))
    st = FlapState(width=fw, height=fh)
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
        flap = key in (ord(" "), curses.KEY_UP, ord("w"), ord("W"))
        alive = st.step(flap=flap)
        try:
            stdscr.clear()
        except curses.error:
            pass
        draw(stdscr, st)
        ui.footer(stdscr, CONTROLS + " | pipes %d" % st.score)
        try:
            stdscr.refresh()
        except curses.error:
            pass
        if not alive:
            entry = scores_mod.get_entry(score_store, GAME_ID)
            _, is_high = scores_mod.record_play(score_store, GAME_ID,
                                                st.score)
            scores_mod.save(score_store)
            ui.game_over_screen(
                stdscr, TITLE,
                ["You threaded %d pipe%s!" % (
                    st.score, "" if st.score == 1 else "s")],
                score=st.score, best=max(entry["high"], st.score),
                is_new_high=is_high, game_id=GAME_ID)
            return
        time.sleep(0.02)
