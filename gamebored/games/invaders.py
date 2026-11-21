"""Space Invaders-style shooter: defend Earth from descending aliens."""

import curses
import random
import time

from .. import scores as scores_mod
from .. import ui

TITLE = "Invaders"
DESCRIPTION = "Shoot the descending aliens"
CONTROLS = "Left/Right or A/D move | Space shoot | p pause | ? help | q menu"
GAME_ID = "invaders"
CATEGORY = "ACTION"

COLS, ROWS = 9, 4


class InvaderState:
    def __init__(self, width=50, height=18, seed=None, level=1):
        self.width = width
        self.height = height
        self.rng = random.Random(seed)
        try:
            level = int(level)
        except (TypeError, ValueError):
            level = 1
        self.level = max(1, level)
        self.ship_x = width // 2
        self.aliens = set()
        self.alien_dir = 1
        self.bullets = []  # (x, y)
        self.bombs = []  # (x, y)
        self.score = 0
        self.over = False
        self.won = False
        self._spawn()

    def _spawn(self):
        self.aliens = set()
        top = 1
        for r in range(ROWS):
            for c in range(COLS):
                x = 4 + c * 4
                y = top + r * 2
                if x < self.width - 2:
                    self.aliens.add((x, y))

    def step(self, move=0, shoot=False):
        if self.over:
            return
        self.ship_x = max(1, min(self.width - 2, self.ship_x + move))
        if shoot and len(self.bullets) < 3:
            self.bullets.append((self.ship_x, self.height - 3))
        # bullets up
        new_bullets = []
        for x, y in self.bullets:
            y -= 1
            if (x, y) in self.aliens:
                self.aliens.discard((x, y))
                self.score += 10 * self.level
            elif y > 0:
                new_bullets.append((x, y))
        self.bullets = new_bullets
        # aliens drift sideways, drop at edges
        edge = any((x + self.alien_dir < 1 or x + self.alien_dir >= self.width - 1)
                   for x, y in self.aliens)
        moved = set()
        if edge:
            self.alien_dir *= -1
            for x, y in self.aliens:
                moved.add((x, y + 1))
        else:
            for x, y in self.aliens:
                moved.add((x + self.alien_dir, y))
        self.aliens = moved
        # alien bombs
        if self.aliens and self.rng.random() < 0.25:
            x, y = self.rng.choice(sorted(self.aliens))
            self.bombs.append((x, y + 1))
        new_bombs = []
        for x, y in self.bombs:
            y += 1
            if y >= self.height - 2 and x in (self.ship_x - 1, self.ship_x,
                                              self.ship_x + 1):
                self.over = True
                self.won = False
                return
            if y < self.height - 1:
                new_bombs.append((x, y))
        self.bombs = new_bombs
        # aliens reached the ship line?
        if any(y >= self.height - 2 for x, y in self.aliens):
            self.over = True
            self.won = False
        if not self.aliens:
            # next wave, faster
            self.level += 1
            self.alien_dir = 1
            self.bombs = []
            self.bullets = []
            self._spawn()


def draw(screen, st, ox, oy):
    for y in range(st.height):
        for x in range(st.width):
            ui.safe_addch(screen, oy + y, ox + x, ord(" "))
    # border
    for x in range(st.width):
        ui.safe_addch(screen, oy - 1, ox + x, ord("-"))
    for x, y in st.aliens:
        ui.safe_addch(screen, oy + y, ox + x, ord("M"),
                      ui.color(2) | curses.A_BOLD)
    for x, y in st.bullets:
        ui.safe_addch(screen, oy + y, ox + x, ord("|"), ui.color(3))
    for x, y in st.bombs:
        ui.safe_addch(screen, oy + y, ox + x, ord("*"), ui.color(5))
    ui.safe_addstr(screen, oy + st.height - 2, ox + st.ship_x - 1, "<^>",
                   ui.color(1) | curses.A_BOLD)
    ui.centered(screen, 0, "INVADERS  score %d  wave %d  aliens %d" % (
        st.score, st.level, len(st.aliens)), ui.color(2) | curses.A_BOLD)


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
    st = InvaderState(fw, fh)
    move = 0
    shoot = False
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
            if ui.pause_overlay(stdscr, TITLE) == "quit":
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
            move = -1
        elif key in (curses.KEY_RIGHT, ord("d"), ord("D")):
            move = 1
        elif key == ord(" "):
            shoot = True
        interval = max(0.05, 0.16 - st.level * 0.015)
        if time.time() - last > interval:
            last = time.time()
            st.step(move, shoot)
            move = 0
            shoot = False
            if st.over:
                entry = scores_mod.get_entry(score_store, GAME_ID)
                _, is_high = scores_mod.record_play(score_store, GAME_ID,
                                                    st.score)
                scores_mod.save(score_store)
                ui.game_over_screen(
                    stdscr, TITLE,
                    ["The aliens landed. Earth needs a rematch!",
                     "Waves cleared: %d" % (st.level - 1)],
                    score=st.score, best=max(entry["high"], st.score),
                    is_new_high=is_high, game_id=GAME_ID, won=False)
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
