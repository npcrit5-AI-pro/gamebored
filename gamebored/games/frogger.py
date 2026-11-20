"""Frogger: hop across the road without getting flattened.

Guide your frog from the bottom verge to the top bank. Cars stream across
the lanes in alternating directions and pick up speed every two crossings.
Five successful crossings wins; three squishes ends the run.
"""

import curses
import random
import time

from .. import scores as scores_mod
from .. import ui

TITLE = "Frogger"
DESCRIPTION = "Hop across the traffic!"
CONTROLS = "Arrows/WASD hop | 5 crossings wins | q/Esc quit"
GAME_ID = "frogger"

LANES = 4
CROSSINGS_TO_WIN = 5
LIVES = 3


class FrogState:
    """Headless road-crossing logic: no curses calls in here."""

    def __init__(self, width=28, lanes=LANES, seed=None):
        self.width = width
        self.lanes = lanes
        self.rng = random.Random(seed)
        self.level = 1
        self.lives = LIVES
        self.crossings = 0
        self.score = 0
        self.over = False
        self.won = False
        self.frog_x = width // 2
        self.frog_y = lanes + 1  # start verge (bottom)
        self.ticks = 0
        self._build_traffic()

    def _build_traffic(self):
        self.traffic = []
        for i in range(self.lanes):
            direction = 1 if i % 2 == 0 else -1
            speed = max(1, 5 - self.level - (i % 2))
            cars = set()
            x = self.rng.randrange(self.width)
            gap = 7
            while x < self.width + gap:
                cars.add(x % self.width)
                x += gap + self.rng.randrange(4)
            self.traffic.append({"dir": direction, "speed": speed,
                                 "cars": cars, "counter": 0})

    def move(self, dx, dy):
        if self.over:
            return
        self.frog_x = max(0, min(self.width - 1, self.frog_x + dx))
        self.frog_y = max(0, min(self.lanes + 1, self.frog_y + dy))
        if self.frog_y == 0:
            self._register_crossing()

    def _register_crossing(self):
        self.crossings += 1
        self.score += 100
        if self.crossings >= CROSSINGS_TO_WIN:
            self.over = True
            self.won = True
            return
        if self.crossings % 2 == 0:
            self.level += 1
        self.frog_x = self.width // 2
        self.frog_y = self.lanes + 1
        self._build_traffic()

    def step(self):
        """Advance traffic one tick; returns False when the run ends."""
        if self.over:
            return False
        self.ticks += 1
        for lane in self.traffic:
            lane["counter"] += 1
            if lane["counter"] >= lane["speed"]:
                lane["counter"] = 0
                moved = set()
                for x in lane["cars"]:
                    moved.add((x + lane["dir"]) % self.width)
                lane["cars"] = moved
        # collision? frog shares a cell with a car on its lane
        if 1 <= self.frog_y <= self.lanes:
            lane = self.traffic[self.frog_y - 1]
            if self.frog_x in lane["cars"]:
                self.lives -= 1
                if self.lives <= 0:
                    self.over = True
                    self.won = False
                    return False
                self.frog_x = self.width // 2
                self.frog_y = self.lanes + 1
        return True


def new_state(width=28, lanes=LANES, seed=None):
    return FrogState(width, lanes, seed)


CAR_CH = {1: ">", -1: "<"}


def draw(screen, st):
    h, w = screen.getmaxyx()
    ui.centered(screen, 1, "FROGGER  cross:%d/%d  lives:%d  score:%d" % (
        st.crossings, CROSSINGS_TO_WIN, st.lives, st.score),
        ui.color(2) | curses.A_BOLD)
    field_w = st.width
    y0 = 3
    x0 = max(0, (w - field_w) // 2)
    # top bank
    ui.safe_addstr(screen, y0, x0, "~" * field_w, ui.color(4))
    for i in range(st.lanes):
        lane = st.traffic[i]
        row = ["-"] * field_w
        for x in lane["cars"]:
            if 0 <= x < field_w:
                row[x] = CAR_CH[lane["dir"]]
        attr = ui.color(5) if i % 2 == 0 else ui.color(3)
        ui.safe_addstr(screen, y0 + 1 + i, x0, "".join(row), attr)
        if 1 <= st.frog_y <= st.lanes and st.frog_y - 1 == i:
            ui.safe_addch(screen, y0 + 1 + i, x0 + st.frog_x, ord("O"),
                           ui.color(2) | curses.A_BOLD)
    ui.safe_addstr(screen, y0 + 1 + st.lanes, x0, "=" * field_w, ui.color(2))
    if st.frog_y == st.lanes + 1:
        ui.safe_addch(screen, y0 + 1 + st.lanes, x0 + st.frog_x, ord("O"),
                       ui.color(2) | curses.A_BOLD)
    if st.frog_y == 0:
        ui.safe_addch(screen, y0, x0 + st.frog_x, ord("O"),
                       ui.color(2) | curses.A_BOLD)
    ui.centered(screen, y0 + st.lanes + 3, "Reach the ~ bank %d times!" %
                CROSSINGS_TO_WIN, ui.color(7))


KEYMAP = {
    curses.KEY_UP: (0, -1), curses.KEY_DOWN: (0, 1),
    curses.KEY_LEFT: (-1, 0), curses.KEY_RIGHT: (1, 0),
    ord("w"): (0, -1), ord("s"): (0, 1), ord("a"): (-1, 0), ord("d"): (1, 0),
    ord("W"): (0, -1), ord("S"): (0, 1), ord("A"): (-1, 0), ord("D"): (1, 0),
}


def play(stdscr, score_store):
    curses.curs_set(0)
    try:
        stdscr.keypad(True)
        stdscr.timeout(90)
    except curses.error:
        pass
    st = FrogState()
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
        if key in KEYMAP:
            dx, dy = KEYMAP[key]
            st.move(dx, dy)
        st.step()
        if st.over:
            entry = scores_mod.get_entry(score_store, GAME_ID)
            _, is_high = scores_mod.record_play(score_store, GAME_ID,
                                                st.score, won=st.won)
            scores_mod.save(score_store)
            ui.game_over_screen(
                stdscr, TITLE,
                ["You crossed %d times. Bank reached!" % st.crossings
                 if st.won else "Squished! You crossed %d times." %
                 st.crossings],
                score=st.score, best=max(entry["high"], st.score),
                is_new_high=is_high, game_id=GAME_ID)
            return
        try:
            stdscr.clear()
        except curses.error:
            pass
        draw(stdscr, st)
        ui.footer(stdscr, CONTROLS + " | score %d" % st.score)
        try:
            stdscr.refresh()
        except curses.error:
            pass
        time.sleep(0.02)
