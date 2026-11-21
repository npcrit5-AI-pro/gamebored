"""Sokoban: push every box onto a target.

Walk into boxes to push them (never pull). Park all boxes on the glowing
targets to clear each room. 205 built-in rooms: 3 tutorial rooms, a curated
Microban selection (David W. Skinner, freely redistributable with credit),
and GameBored reverse-pulled extras. Finish them all to unlock endless
procedurally generated rooms. R restarts the room. Your raw score is
100 points per box plus 500 per cleared room.

Only the standard library is used.
"""

import curses
import random

from .. import progress as progress_mod
from .. import scores as scores_mod
from .. import ui
from . import sokoban_data as data_mod
from . import sokoban_solver as solver_mod

TITLE = "Sokoban"
DESCRIPTION = "Push boxes onto targets"
CONTROLS = ("Arrows/WASD push | r restart | u undo | p pause | ? help | q menu")
GAME_ID = "sokoban"
CATEGORY = "PUZZLE"

LEVELS = data_mod.LEVELS

BOX_POINTS = 100
ROOM_BONUS = 500


class SokState:
    """Headless box-pushing logic: no curses calls in here."""

    def __init__(self, level=0, rows=None, endless=None):
        try:
            level = int(level)
        except (TypeError, ValueError):
            level = 0
        self.level = max(0, min(level, len(LEVELS) - 1))
        self.endless = endless  # (seed, n) or None
        self.moves = 0
        self.score = 0
        self.over = False
        self.won = False
        self.history = []
        if rows is not None:
            self._load_row(None, endless_rows=rows)
        elif endless is not None:
            self._load_row(None,
                           endless_rows=gen_endless_verified(endless[0],
                                                             endless[1]))
        else:
            self._load_row(self.level)

    def _load_row(self, level, endless_rows=None):
        rows = endless_rows if endless_rows is not None else LEVELS[level]
        walls, targets, boxes, player, W, H = solver_mod.parse(rows)
        self.walls = walls
        self.targets = targets
        self.boxes = boxes
        self.player = player if player is not None else (1, 1)
        self.height = H
        self.width = W

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
        self.history.append((self.player, set(self.boxes), self.moves,
                             self.score, self.over, self.won))
        if len(self.history) > 2000:
            del self.history[:-2000]
        if (nx, ny) in self.boxes:
            bx, by = nx + dx, ny + dy
            self.boxes.discard((nx, ny))
            self.boxes.add((bx, by))
        self.player = (nx, ny)
        self.moves += 1
        if self.solved:
            self.score += len(self.boxes) * BOX_POINTS + ROOM_BONUS
            self.over = True
            self.won = True
        return True

    def undo(self):
        """Take back the last move. Returns True if anything was undone."""
        if not self.history:
            return False
        player, boxes, moves, score, over, won = self.history.pop()
        self.player = player
        self.boxes = boxes
        self.moves = moves
        self.score = score
        self.over = over
        self.won = won
        return True

    def restart(self):
        self.moves = 0
        self.over = False
        self.won = False
        self.score = 0
        self.history = []
        if self.endless is None:
            self._load_row(self.level)
        else:
            seed, n = self.endless
            rows = gen_endless_verified(seed, n)
            self._load_row(None, endless_rows=rows)


def new_state(level=0):
    return SokState(level)


# --------------------------------------------------------------------------
# Endless generated rooms (seeded reverse-pulls, solver-verified)
# --------------------------------------------------------------------------

def gen_endless_rows(seed, n):
    """Seeded endless room n (difficulty rises with n)."""
    n = int(n)
    rng = random.Random("sokoban:%s:%s" % (seed, n))
    d = min(1.0, 0.15 + 0.05 * n)
    W = min(19, 9 + n // 4)
    H = min(13, 8 + n // 5)
    nboxes = min(5, 2 + n // 6)
    walls = set()
    for x in range(W):
        walls.add((x, 0))
        walls.add((x, H - 1))
    for y in range(H):
        walls.add((0, y))
        walls.add((W - 1, y))
    floors = [(x, y) for y in range(1, H - 1) for x in range(1, W - 1)]
    targets = set(rng.sample(floors, nboxes))
    boxes = set(targets)
    player = rng.choice([c for c in floors if c not in boxes])
    pulls = min(90, 20 + 4 * n)

    def free(c):
        return c not in walls and c not in boxes

    for _ in range(pulls):
        if rng.random() < 0.45:
            cands = []
            for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
                adj = (player[0] + dx, player[1] + dy)
                behind = (player[0] - dx, player[1] - dy)
                if adj in boxes and behind not in walls and behind not in boxes:
                    cands.append((dx, dy))
            if cands:
                dx, dy = rng.choice(cands)
                adj = (player[0] + dx, player[1] + dy)
                behind = (player[0] - dx, player[1] - dy)
                boxes.discard(adj)
                boxes.add(player)
                player = behind
                continue
        opts = [(player[0] + dx, player[1] + dy)
                for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0))]
        opts = [c for c in opts if free(c)]
        if opts:
            player = rng.choice(opts)
    if not boxes or frozenset(boxes) <= targets:
        return None  # scrambled back to solved: not a puzzle
    rows = []
    for y in range(H):
        row = ""
        for x in range(W):
            c = (x, y)
            if c in walls:
                row += "#"
            elif c == player and c in targets:
                row += "+"
            elif c == player:
                row += "@"
            elif c in boxes and c in targets:
                row += "*"
            elif c in boxes:
                row += "$"
            elif c in targets:
                row += "."
            else:
                row += " "
        rows.append(row)
    return tuple(rows)


def gen_endless_verified(seed, n, tries=30):
    """Return solver-verified endless rows for (seed, n)."""
    for k in range(tries):
        rows = gen_endless_rows(seed if k == 0 else "%s#%d" % (seed, k), n)
        if rows is None:
            continue
        if solver_mod.solve_pushes(rows, cap=20000,
                                   time_limit=2.0) is not None:
            return rows
    # fallback: tiny 1-box room (trivially solvable)
    return (
        "#####",
        "# . #",
        "# $ #",
        "# @ #",
        "#####",
    )


def draw(screen, st, total_score, label=None):
    h, w = screen.getmaxyx()
    if label is None:
        if st.endless is not None:
            label = "SOKOBAN end:%d seed:%s moves:%d score:%d" % (
                st.endless[1], st.endless[0], st.moves, total_score)
        else:
            label = "SOKOBAN room:%d/%d moves:%d score:%d" % (
                st.level + 1, len(LEVELS), st.moves, total_score)
    ui.centered(screen, 1, label, ui.color(3) | curses.A_BOLD)
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


def select_level(stdscr, score_store, progress):
    """Level-select: pick an unlocked room, or endless once unlocked."""
    total = len(LEVELS)
    unlocked = progress_mod.get_unlocked(progress, GAME_ID, total)
    endless_ok = progress_mod.endless_unlocked(progress, GAME_ID, total)
    sel = min(unlocked, total - 1)
    mode = "level"
    while True:
        if ui.too_small(stdscr):
            ui.show_too_small(stdscr)
            try:
                key = stdscr.getch()
            except curses.error:
                key = -1
            if key in ui.QUIT_KEYS:
                return None
            continue
        try:
            stdscr.clear()
            h, w = stdscr.getmaxyx()
            ui.header(stdscr, "SOKOBAN: PICK A ROOM",
                      "%d rooms + endless" % total if endless_ok else
                      "clear rooms to unlock more")
            top = 3
            visible = max(1, h - top - 3)
            # show window around selection
            cur = sel if mode == "level" else total
            start = max(0, min(cur - visible // 2, total + 1 - visible))
            for i in range(start, min(total + 1, start + visible)):
                if i < total:
                    locked = i > unlocked
                    line = "room %3d%s" % (i + 1,
                                           " [locked]" if locked else "")
                else:
                    locked = not endless_ok
                    line = "endless mode%s" % (
                        " (generated forever)" if endless_ok
                        else " [finish all %d to unlock]" % total)
                line = ("-> " if i == cur else "   ") + line
                attr = ui.color(7) if locked else (
                    curses.A_REVERSE | curses.A_BOLD if i == cur
                    else ui.color(3))
                ui.safe_addstr(stdscr, top + i - start,
                               max(2, (w - 40) // 2), line[: w - 4], attr)
            ui.footer(stdscr, "Up/Down pick | Enter play | e endless | "
                              "q menu")
            stdscr.refresh()
        except curses.error:
            pass
        try:
            key = stdscr.getch()
        except curses.error:
            key = -1
        if key in ui.QUIT_KEYS:
            return None
        if key == curses.KEY_UP:
            if mode == "level":
                sel = (sel - 1) % (unlocked + 1)
            else:
                mode = "level"
        elif key == curses.KEY_DOWN:
            if mode == "level":
                if sel < unlocked:
                    sel += 1
                elif endless_ok:
                    mode = "endless"
            else:
                mode = "level"
                sel = 0
        elif key in (ord("e"), ord("E")):
            if endless_ok:
                return ("endless", None)
        elif key in (10, 13, curses.KEY_ENTER, ord(" ")):
            if mode == "endless":
                if endless_ok:
                    return ("endless", None)
            else:
                return ("level", min(sel, unlocked))
        elif key == curses.KEY_RESIZE:
            continue


def play(stdscr, score_store):
    curses.curs_set(0)
    try:
        stdscr.keypad(True)
        stdscr.timeout(-1)
    except curses.error:
        pass
    progress = progress_mod.load()
    total = len(LEVELS)
    pick = select_level(stdscr, score_store, progress)
    if pick is None:
        return
    kind, idx = pick
    if kind == "endless":
        seed = str(random.Random().randrange(1 << 30))
        n = 1
        st = SokState(rows=gen_endless_verified(seed, n), endless=(seed, n))
        total_score = 0
    else:
        st = SokState(idx)
        total_score = 0
        level_idx = idx
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
        if kind == "endless":
            draw(stdscr, st, total_score,
                 label="Generated level %d seed:%s moves:%d score:%d" % (
                     n, seed, st.moves, total_score))
        else:
            draw(stdscr, st, total_score)
        ui.game_footer(stdscr, CONTROLS + " | home %d/%d" % (
            st.boxes_home, len(st.boxes)))
        try:
            stdscr.refresh()
        except curses.error:
            pass
        if st.over:
            total_score += st.score
            if kind == "endless":
                n += 1
                st = SokState(rows=gen_endless_verified(seed, n),
                              endless=(seed, n))
                st.score = 0
                continue
            progress = progress_mod.load()
            progress_mod.record_level_complete(progress, GAME_ID,
                                               level_idx, total)
            if level_idx + 1 >= total:
                seed = str(random.Random().randrange(1 << 30))
                n = 1
                kind = "endless"
                st = SokState(rows=gen_endless_verified(seed, n),
                              endless=(seed, n))
                st.score = 0
                continue
            level_idx += 1
            st = SokState(level_idx)
            st.score = 0
            continue
        try:
            key = stdscr.getch()
        except curses.error:
            key = -1
        if key in ui.QUIT_KEYS:
            scores_mod.record_play(score_store, GAME_ID, total_score,
                                   won=False)
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
        elif key in (ord("u"), ord("U")):
            st.undo()
        elif key in KEYMAP:
            dx, dy = KEYMAP[key]
            st.move(dx, dy)
