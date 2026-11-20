"""Sokoban: push every box onto a target.

Walk into boxes to push them (never pull). Park all boxes on the glowing
targets to clear each of the 3 rooms. R restarts the room. Your raw score
is 100 points per box plus 500 per cleared room.
"""

import curses

from .. import scores as scores_mod
from .. import ui

TITLE = "Sokoban"
DESCRIPTION = "Push boxes onto targets"
CONTROLS = "Arrows/WASD push | r restart room | p pause | ? help | q menu"
GAME_ID = "sokoban"
CATEGORY = "PUZZLE"

LEVELS = (
    (
        "#######",
        "#  .  #",
        "#  $  #",
        "#  @  #",
        "#######",
    ),
    (
        "########",
        "#  . . #",
        "#  $ $ #",
        "#   @  #",
        "########",
    ),
    (
        "#########",
        "# . . . #",
        "# $ $ $ #",
        "#   @   #",
        "#########",
    ),
)

BOX_POINTS = 100
ROOM_BONUS = 500


class SokState:
    """Headless box-pushing logic: no curses calls in here."""

    def __init__(self, level=0):
        self.level = level
        self.moves = 0
        self.score = 0
        self.over = False
        self.won = False
        self._load(level)

    def _load(self, level):
        rows = LEVELS[level]
        self.walls = set()
        self.targets = set()
        self.boxes = set()
        self.player = (1, 1)
        for y, row in enumerate(rows):
            for x, ch in enumerate(row):
                if ch == "#":
                    self.walls.add((x, y))
                elif ch == ".":
                    self.targets.add((x, y))
                elif ch == "$":
                    self.boxes.add((x, y))
                elif ch == "@":
                    self.player = (x, y)
        self.height = len(rows)
        self.width = max(len(r) for r in rows)

    @property
    def boxes_home(self):
        return sum(1 for b in self.boxes if b in self.targets)

    @property
    def solved(self):
        return bool(self.boxes) and self.boxes <= self.targets

    def move(self, dx, dy):
        """Try to step; returns True if the player moved."""
        if self.over:
            return False
        px, py = self.player
        nx, ny = px + dx, py + dy
        if (nx, ny) in self.walls:
            return False
        if (nx, ny) in self.boxes:
            bx, by = nx + dx, ny + dy
            if (bx, by) in self.walls or (bx, by) in self.boxes:
                return False
            self.boxes.discard((nx, ny))
            self.boxes.add((bx, by))
        self.player = (nx, ny)
        self.moves += 1
        if self.solved:
            self.score += len(self.boxes) * BOX_POINTS + ROOM_BONUS
            if self.level + 1 >= len(LEVELS):
                self.over = True
                self.won = True
            else:
                self.level += 1
                self.moves = 0
                self._load(self.level)
        return True

    def restart(self):
        self.moves = 0
        self._load(self.level)


def new_state(level=0):
    return SokState(level)


def draw(screen, st, total_score):
    h, w = screen.getmaxyx()
    ui.centered(screen, 1, "SOKOBAN  room:%d/%d  moves:%d  score:%d" % (
        st.level + 1, len(LEVELS), st.moves, total_score),
        ui.color(3) | curses.A_BOLD)
    y0 = max(2, (h - st.height) // 2)
    x0 = max(0, (w - st.width) // 2)
    for y in range(st.height):
        for x in range(st.width):
            pos = (x, y)
            if pos in st.walls:
                ch, attr = "#", ui.color(7)
            elif pos == st.player:
                ch, attr = "@", ui.color(2) | curses.A_BOLD
            elif pos in st.boxes and pos in st.targets:
                ch, attr = "*", ui.color(8) | curses.A_BOLD
            elif pos in st.boxes:
                ch, attr = "$", ui.color(3) | curses.A_BOLD
            elif pos in st.targets:
                ch, attr = ".", ui.color(4) | curses.A_BOLD
            else:
                ch, attr = " ", 0
            ui.safe_addch(screen, y0 + y, x0 + x, ord(ch), attr)


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
        stdscr.timeout(-1)
    except curses.error:
        pass
    st = SokState()
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
        draw(stdscr, st, st.score)
        ui.game_footer(stdscr, CONTROLS + " | home %d/%d" % (
            st.boxes_home, len(st.boxes)))
        try:
            stdscr.refresh()
        except curses.error:
            pass
        if st.over:
            entry = scores_mod.get_entry(score_store, GAME_ID)
            _, is_high = scores_mod.record_play(score_store, GAME_ID,
                                                st.score, won=st.won)
            scores_mod.save(score_store)
            ui.game_over_screen(
                stdscr, TITLE,
                ["All rooms cleared, warehouse hero!" if st.won
                 else "Room %d unfinished." % (st.level + 1)],
                score=st.score, best=max(entry["high"], st.score),
                is_new_high=is_high, game_id=GAME_ID, won=st.won)
            return
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
            continue
        if key in ui.HELP_KEYS:
            ui.show_help_overlay(stdscr, TITLE, CONTROLS)
            continue
        if key == curses.KEY_RESIZE:
            continue
        if key in (ord("r"), ord("R")):
            st.restart()
        elif key in KEYMAP:
            dx, dy = KEYMAP[key]
            st.move(dx, dy)
