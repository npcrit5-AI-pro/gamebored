"""Runner: a side-view platformer. Run, jump, dodge, grab the exit door.

Sprint across 60 handcrafted rooms (plus endless procedurally generated
rooms after that): leap pits, hop platforms, dodge spikes and patrolling
critters, ride moving platforms, grab keys for locked doors, and touch the
X exit. Coins are worth 10, each cleared room 200. 3 lives per room.

Only the standard library is used.
"""

import curses
import random
import time

from .. import progress as progress_mod
from .. import scores as scores_mod
from .. import ui

TITLE = "Runner"
DESCRIPTION = "Run, jump, dodge, exit!"
CONTROLS = ("Arrows/WASD move + jump | reach X | r restart room | p pause | ? help | q menu")
GAME_ID = "platformer"
CATEGORY = "ACTION"

COIN_POINTS = 10
ROOM_BONUS = 200
LIVES = 3

GRAV = 25.0
MOVE_SPEED = 5.2
JUMP_V = 12.0
PW, PH = 0.7, 0.9  # player width/height in tiles

try:
    from . import platformer_data as _data
    LEVELS = _data.LEVELS
except Exception:
    LEVELS = ()

SOLID_CH = "#"
SPIKE_CH = "^"


# --------------------------------------------------------------------------
# Level model
# --------------------------------------------------------------------------

def parse_level(rows):
    """Parse ASCII rows into a level dict (no curses)."""
    H = len(rows)
    W = max((len(r) for r in rows), default=0)
    rows = [r.ljust(W) for r in rows]
    walls, spikes, coins = set(), set(), set()
    doors, enemies = set(), []
    m_cells = set()
    spawn, exit_ = (1, 1), (W - 2, H - 2)
    key = None
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch == "#":
                walls.add((x, y))
            elif ch == "^":
                spikes.add((x, y))
            elif ch == "C":
                coins.add((x, y))
            elif ch == "K":
                key = (x, y)
            elif ch == "D":
                doors.add((x, y))
            elif ch == "E":
                enemies.append((x, y))
            elif ch == "M":
                m_cells.add((x, y))
            elif ch == "P":
                spawn = (x, y)
            elif ch == "X":
                exit_ = (x, y)
    # contiguous horizontal runs of M form moving platforms
    platforms = []
    by_row = {}
    for (x, y) in m_cells:
        by_row.setdefault(y, []).append(x)
    for y, xs in by_row.items():
        xs.sort()
        run = [xs[0]]
        for x in xs[1:]:
            if x == run[-1] + 1:
                run.append(x)
            else:
                platforms.append({"y": y, "x0": run[0], "w": len(run),
                                  "phase": (run[0] + y) % 4})
                run = [x]
        platforms.append({"y": y, "x0": run[0], "w": len(run),
                          "phase": (run[0] + y) % 4})
    return {"rows": rows, "W": W, "H": H, "walls": walls, "spikes": spikes,
            "coins": coins, "key": key, "doors": doors, "enemies": enemies,
            "platforms": platforms, "spawn": spawn, "exit": exit_}


def platform_cells(lv, tick):
    """Current solid cells of moving platforms (oscillate horizontally)."""
    cells = set()
    for i, p in enumerate(lv["platforms"]):
        amp = 2
        off = round(amp * _tri((tick + p["phase"] * 17) / 40.0 + i * 0.37))
        for k in range(p["w"]):
            cells.add((p["x0"] + off + k, p["y"]))
    return cells


def _tri(t):
    """Triangle wave in [-1, 1]."""
    t = t % 2.0
    return (t if t < 1.0 else 2.0 - t) * 2.0 - 1.0


def solids(lv, tick, doors_open):
    s = set(lv["walls"])
    if not doors_open:
        s |= lv["doors"]
    s |= platform_cells(lv, tick)
    return s


# --------------------------------------------------------------------------
# Reachability solver (used by tests + endless verification)
# --------------------------------------------------------------------------

def beatable(rows):
    """True if the exit is reachable from spawn via run/jump moves.

    Conservative geometric model: walk adjacent cells, climb 1-2 high steps,
    running-jump gaps (dx<=5 flat, rise<=2 with dx<=4), fall any distance
    with dx<=6. Spikes are never landed on; enemies are ignored (timing);
    moving platforms count as static solids; locked doors need the key.
    """
    lv = parse_level(rows)
    W, H = lv["W"], lv["H"]
    solid = set(lv["walls"]) | {c for p in lv["platforms"]
                                for c in [(p["x0"] + k, p["y"])
                                          for k in range(p["w"])]}
    doors = set(lv["doors"])

    def standable(cell, doors_open):
        x, y = cell
        if not (0 <= x < W and 0 <= y < H):
            return False
        if cell in solid:
            return False
        if not doors_open and cell in doors:
            return False
        if cell in lv["spikes"]:
            return False
        below = (x, y + 1)
        if y + 1 >= H:
            return True
        if below in solid:
            return True
        if not doors_open and below in doors:
            return True
        return False

    def blocked_rect(x0, y0, x1, y1, doors_open):
        xa, xb = sorted((x0, x1))
        ya, yb = sorted((y0, y1))
        for x in range(xa, xb + 1):
            for y in range(ya, yb):
                # rows strictly between the endpoints must be free of solids
                # (landing/start rows handled by standable checks)
                if (x, y) in solid:
                    return True
                if not doors_open and (x, y) in doors:
                    return True
        return False

    from collections import deque

    def search(doors_open):
        start = lv["spawn"]
        goal = lv["exit"]
        if not standable(start, doors_open):
            # spawn inside wall? allow: drop until standable
            sx, sy = start
            while sy < H and not standable((sx, sy), doors_open):
                sy += 1
            start = (sx, sy)
        seen = {start}
        q = deque([start])
        while q:
            x, y = q.popleft()
            if (x, y) == goal or \
                    abs(x - goal[0]) + abs(y - goal[1]) <= 1 and \
                    standable(goal, doors_open):
                # adjacent to exit counts (touching wins in-game)
                return True, set(q) | seen
            # walk + step up/down
            for dx in (-1, 1):
                for dy, maxdrop in ((0, 0), (-1, 0), (-2, 0), (1, 0)):
                    n = (x + dx, y + dy)
                    if dy == 1 and not standable(n, doors_open):
                        n = (x + dx, y + 2)
                        if not standable(n, doors_open):
                            continue
                    elif not standable(n, doors_open):
                        continue
                    if n not in seen:
                        if dy < 0 and blocked_rect(x, y - 1, n[0], n[1],
                                                   doors_open):
                            pass
                        else:
                            seen.add(n)
                            q.append(n)
            # running jumps / falls
            for dx in range(-5, 6):
                if dx == 0:
                    continue
                for dy in range(-2, 7):
                    if dy == 0 and abs(dx) <= 1:
                        continue
                    if dy < 0 and (abs(dx) > 4 or dy < -2):
                        continue
                    if dy >= 0 and abs(dx) > 6:
                        continue
                    n = (x + dx, y + dy)
                    if n in seen:
                        continue
                    if not (0 <= n[0] < W and 0 <= n[1] < H):
                        continue
                    if not standable(n, doors_open):
                        continue
                    if blocked_rect(x, y - (1 if dy < 0 else 0),
                                    n[0], n[1], doors_open):
                        continue
                    seen.add(n)
                    q.append(n)
        return False, seen

    if not lv["doors"]:
        ok, _ = search(True)
        return ok
    ok_closed, seen = search(False)
    if ok_closed:
        return True
    # key needed: is the key reachable without opening doors?
    key = lv["key"]
    if key is None:
        return False
    # reachable set from search above; check key standable+seen
    if key in seen or any(abs(key[0] - s[0]) + abs(key[1] - s[1]) <= 1
                          for s in seen):
        ok_open, _ = search(True)
        return ok_open
    return False


# --------------------------------------------------------------------------
# Procedural endless levels (seeded, solver-verified)
# --------------------------------------------------------------------------

def gen_endless_rows(seed, n):
    """Build endless room number n (1-based past built-ins) for seed."""
    n = int(n)
    rng = random.Random("runner:%s:%s" % (seed, n))
    d = min(1.0, 0.18 + 0.06 * n)  # difficulty 0..1
    W = min(70, 36 + n)
    H = 14
    ground = H - 3
    grid = [[" "] * W for _ in range(H)]
    for x in range(W):
        for y in (ground + 1, ground + 2, H - 1):
            if y < H:
                grid[y][x] = "#"
    grid[H - 1] = ["#"] * W
    # pits
    x = 8
    while x < W - 8:
        if rng.random() < 0.35 + 0.35 * d:
            gap = rng.choice([2, 2, 3, 3, 4] if d > 0.4 else [2, 2, 3])
            gap = min(gap, 4)
            for gx in range(x, min(x + gap, W - 1)):
                for y in (ground + 1, ground + 2):
                    grid[y][gx] = " "
            # coin arc over the pit
            if rng.random() < 0.7:
                for gx in range(x, min(x + gap, W - 1)):
                    if ground - 2 >= 0:
                        grid[ground - 2][gx] = "C"
            x += gap + rng.randrange(3, 7)
        else:
            x += rng.randrange(3, 6)
    # floating platforms with coins
    nplat = rng.randrange(3, 5 + int(4 * d))
    for _ in range(nplat):
        px = rng.randrange(4, W - 8)
        py = rng.randrange(max(2, ground - 6), ground - 1)
        w = rng.choice([3, 3, 4, 4, 5])
        for k in range(w):
            if 0 < px + k < W - 1:
                grid[py][px + k] = "#"
        if rng.random() < 0.8 and py - 1 >= 0:
            for k in range(w):
                if grid[py - 1][px + k] == " " and rng.random() < 0.7:
                    grid[py - 1][px + k] = "C"
    # spikes on ground (jumpable singles/doubles)
    nsp = int(rng.randrange(1, 3) + 3 * d)
    for _ in range(nsp):
        sx = rng.randrange(6, W - 6)
        if grid[ground][sx] == " " and grid[ground + 1][sx] == "#":
            grid[ground][sx] = "^"
            if d > 0.5 and rng.random() < 0.4 and grid[ground][sx + 1] == " ":
                grid[ground][sx + 1] = "^"
    # enemies
    nen = int(rng.randrange(1, 2) + 3 * d)
    for _ in range(nen):
        ex = rng.randrange(5, W - 5)
        if grid[ground][ex] == " " and grid[ground + 1][ex] == "#":
            grid[ground][ex] = "E"
    # key + door for harder rooms
    if d > 0.35 and rng.random() < 0.8:
        dx = rng.randrange(W - 14, W - 6)
        for y in (ground - 1, ground):
            grid[y][dx] = "D"
        kx = rng.randrange(4, max(5, dx - 6))
        ky = rng.randrange(max(1, ground - 5), ground)
        if grid[ky][kx] == " ":
            grid[ky][kx] = "K"
        else:
            grid[max(1, ky - 1)][kx] = "K"
    # moving platform over a wide pit for variety at higher difficulty
    if d > 0.45 and rng.random() < 0.7:
        mx = rng.randrange(10, max(11, W - 14))
        my = ground - 1
        for k in range(3):
            grid[my][mx + k] = "M"
    grid[ground][1] = "P"
    # exit: rightmost ground cell, clear around it
    ex = W - 2
    grid[ground][ex] = "X"
    if grid[ground][ex - 1] == "^":
        grid[ground][ex - 1] = " "
    return tuple("".join(r).rstrip() for r in grid)


def gen_endless_verified(seed, n, tries=25):
    """Return (rows, n) verified beatable; retries with sub-seeds."""
    n = int(n)
    for k in range(tries):
        key = seed if k == 0 else "%s#%d" % (seed, k)
        rows = gen_endless_rows(key, n)
        if beatable(rows):
            return rows, n
    rows = gen_endless_rows(seed, 1)
    if beatable(rows):
        return rows, 1
    # fallback: flat walkable room (trivially beatable)
    W = 40
    rows = tuple(
        ("#" * W if y >= 11 else ("#P" + " " * (W - 4) + "X#" if y == 10
                                  else "#" + " " * (W - 2) + "#"))
        for y in range(14))
    return rows, n


# --------------------------------------------------------------------------
# Headless physics state
# --------------------------------------------------------------------------

class RunState:
    def __init__(self, rows, score=0, endless=None):
        if not isinstance(rows, (list, tuple)) or not rows:
            rows = LEVELS[0] if LEVELS else ("#####", "#P X#", "#####")
        self.lv = parse_level(rows)
        self.score = score
        self.endless = endless  # (seed, n) or None
        self.lives = LIVES
        self.over = False
        self.won = False  # True when the room's exit is reached
        self.dead = False
        self.tick = 0
        sx, sy = self.lv["spawn"]
        self.x, self.y = float(sx), float(sy)
        self.vx = self.vy = 0.0
        self.grounded = False
        self.coins = set(self.lv["coins"])
        self.has_key = False
        self.enemies = [{"x": float(ex), "y": float(ey), "dir": 1.0,
                         "speed": 2.0} for ex, ey in self.lv["enemies"]]
        self._plat_prev = {}

    @property
    def doors_open(self):
        return self.has_key or not self.lv["doors"]

    def solids(self):
        return solids(self.lv, self.tick, self.doors_open)

    def _collide_x(self, s):
        """Resolve horizontal overlap (torso only, so ground is ignored)."""
        cells = self._overlap(self.x, self.y, s, ypad_top=0.05,
                              ypad_bot=0.15)
        if not cells:
            return False
        if self.vx > 0:
            self.x = min(cx for cx, _ in cells) - PW - 0.001
        elif self.vx < 0:
            self.x = max(cx for cx, _ in cells) + 1 + 0.001
        else:
            return True
        self.vx = 0.0
        return True

    def _collide_y(self, s):
        """Resolve vertical overlap; True when something was hit."""
        cells = self._overlap(self.x, self.y, s)
        if not cells:
            return False
        if self.vy > 0:
            self.y = min(cy for _, cy in cells) - PH - 0.001
        elif self.vy < 0:
            self.y = max(cy for _, cy in cells) + 1 + 0.001
        else:
            return True
        self.vy = 0.0
        return True

    def _collide(self, s):
        """Resolve AABB overlap vs solid cells (X first, then Y)."""
        hx = self._collide_x(s)
        hy = self._collide_y(s)
        return hx, hy

    def _overlap(self, x, y, s, ypad_top=0.0, ypad_bot=0.0):
        x0, x1 = int(x), int(x + PW - 1e-6)
        y0 = int(y + ypad_top)
        y1 = int(y + PH - 1e-6 - ypad_bot)
        out = []
        for cx in range(x0, x1 + 1):
            for cy in range(y0, y1 + 1):
                if (cx, cy) in s:
                    out.append((cx, cy))
        return out

    def step(self, dt, move=0, jump=False):
        """Advance physics by dt seconds. Returns 'dead'/'won'/None."""
        if self.over:
            return "over"
        try:
            dt = float(dt)
        except (TypeError, ValueError):
            dt = 0.0
        if dt != dt or dt == float("inf") or dt == float("-inf"):
            dt = 0.0
        dt = max(0.0, min(dt, 1.0))
        try:
            move = float(move)
        except (TypeError, ValueError):
            move = 0.0
        if move != move:  # NaN input drifts nowhere
            move = 0.0
        move = max(-1.0, min(move, 1.0))
        self.tick += 1
        s = self.solids()
        # moving platform carry
        cur = platform_cells(self.lv, self.tick)
        prev = platform_cells(self.lv, self.tick - 1)
        # horizontal input
        self.vx = float(move) * MOVE_SPEED
        # gravity
        self.vy += GRAV * dt
        if self.vy > 14.0:
            self.vy = 14.0
        # jump
        if jump and self.grounded:
            self.vy = -JUMP_V
            self.grounded = False
        # integrate X
        self.x += self.vx * dt
        self._collide(s)
        # integrate Y in substeps for stability
        steps = 3
        self.grounded = False
        for _ in range(steps):
            self.y += (self.vy * dt) / steps
            _, hy = self._collide(s)
            if hy and self.vy == 0.0:
                # landed or bonked; check ground below
                probe = self._overlap(self.x, self.y + 0.05, s)
                if probe:
                    self.grounded = True
        # ground probe
        if not self.grounded:
            if self._overlap(self.x, self.y + 0.08, s):
                self.grounded = True
                if self.vy > 0:
                    self.vy = 0.0
        # carry by platform
        for (cx, cy) in self._overlap(self.x, self.y + 0.12, s):
            if (cx, cy) in cur:
                # find this platform's delta
                for p in self.lv["platforms"]:
                    cells_now = {(p["x0"] + round(
                        2 * _tri((self.tick + p["phase"] * 17) / 40.0)) + k,
                        p["y"]) for k in range(p["w"])}
                    cells_prv = {(p["x0"] + round(
                        2 * _tri((self.tick - 1 + p["phase"] * 17) / 40.0))
                        + k, p["y"]) for k in range(p["w"])}
                    if (cx, cy) in cells_now:
                        dx = sum(c[0] for c in cells_now) / len(cells_now) - \
                            sum(c[0] for c in cells_prv) / len(cells_prv)
                        self.x += dx
                        break
                break
        self._collide(s)
        # enemies
        for e in self.enemies:
            e["x"] += e["dir"] * e["speed"] * dt
            ahead = int(e["x"] + (0.9 if e["dir"] > 0 else -0.1))
            ey = int(e["y"])
            if (ahead, ey) in s or (ahead, ey + 1) not in s:
                e["dir"] *= -1.0
                e["x"] += e["dir"] * e["speed"] * dt * 2
        # pickups / hazards
        pcx, pcy = self.x + PW / 2, self.y + PH / 2
        cell = (int(pcx), int(pcy))
        cells_hit = {(int(self.x + dx), int(self.y + dy))
                     for dx in (0.05, PW - 0.05) for dy in (0.05, PH - 0.05)}
        for c in list(cells_hit):
            if c in self.coins:
                self.coins.discard(c)
                self.score += COIN_POINTS
            if self.lv["key"] is not None and c == self.lv["key"] \
                    and not self.has_key:
                self.has_key = True
        ex, ey = self.lv["exit"]
        if any(abs((self.x + PW / 2) - (ex + 0.5)) < 0.8 and
               abs((self.y + PH / 2) - (ey + 0.5)) < 0.9 for _ in [0]):
            self.score += ROOM_BONUS
            self.over = True
            self.won = True
            return "won"
        for c in cells_hit:
            if c in self.lv["spikes"]:
                return self._die()
        for e in self.enemies:
            if abs((self.x + PW / 2) - (e["x"] + 0.5)) < 0.75 and \
                    abs((self.y + PH / 2) - (e["y"] + 0.5)) < 0.8:
                return self._die()
        if self.y > self.lv["H"] + 1:
            return self._die()
        return None

    def _die(self):
        self.lives -= 1
        if self.lives <= 0:
            self.over = True
            self.won = False
            self.dead = True
            return "dead-over"
        # respawn at spawn, restore coins/key of this room attempt
        sx, sy = self.lv["spawn"]
        self.x, self.y = float(sx), float(sy)
        self.vx = self.vy = 0.0
        self.coins = set(self.lv["coins"])
        self.has_key = False
        self.enemies = [{"x": float(ex), "y": float(ey), "dir": 1.0,
                         "speed": 2.0} for ex, ey in self.lv["enemies"]]
        return "dead"


def new_state(level=0, score=0, endless=None, seed=None, endless_n=None):
    if endless is not None:
        rows, _ = gen_endless_verified(endless, endless_n or 1)
        return RunState(rows, score=score, endless=(endless, endless_n or 1))
    try:
        level = int(level)
    except (TypeError, ValueError):
        level = 0
    level = max(0, min(level, len(LEVELS) - 1)) if LEVELS else 0
    rows = LEVELS[level]
    return RunState(rows, score=score)


# --------------------------------------------------------------------------
# Drawing + input
# --------------------------------------------------------------------------

def draw(screen, st, label):
    h, w = screen.getmaxyx()
    ui.centered(screen, 1, label, ui.color(3) | curses.A_BOLD)
    lv = st.lv
    W, H = lv["W"], lv["H"]
    y0 = max(2, (h - H) // 2)
    x0 = max(0, (w - W) // 2)
    s = st.solids()
    cur = platform_cells(lv, st.tick)
    for y in range(H):
        if y0 + y >= h - 1:
            break
        for x in range(W):
            if x0 + x >= w:
                break
            pos = (x, y)
            if pos in s and pos not in lv["walls"] and pos not in lv["doors"]:
                ch, attr = ("=", ui.color(6) | curses.A_BOLD)  # moving
            elif pos in lv["walls"]:
                ch, attr = ("#", ui.color(7))
            elif not st.doors_open and pos in lv["doors"]:
                ch, attr = ("D", ui.color(5) | curses.A_BOLD)
            elif pos in st.coins:
                ch, attr = ("o", ui.color(3) | curses.A_BOLD)
            elif pos in lv["spikes"]:
                ch, attr = ("^", ui.color(5) | curses.A_BOLD)
            elif lv["key"] is not None and pos == lv["key"] \
                    and not st.has_key:
                ch, attr = ("K", ui.color(8) | curses.A_BOLD)
            elif pos == lv["exit"]:
                ch, attr = ("X", ui.color(2) | curses.A_BOLD)
            elif pos in lv["doors"]:
                ch, attr = (" ", 0)  # open door
            else:
                ch, attr = (" ", 0)
            # enemies overlay
            for e in st.enemies:
                if (int(e["x"]), int(e["y"])) == pos:
                    ch, attr = ("M", ui.color(5) | curses.A_BOLD)
            ui.safe_addch(screen, y0 + y, x0 + x, ord(ch), attr)
    # player overlay
    px = x0 + int(st.x + PW / 2)
    py = y0 + int(st.y + PH / 2)
    ui.safe_addch(screen, py, px, ord("@"),
                  ui.color(2) | curses.A_BOLD)
    if st.has_key:
        ui.safe_addstr(screen, y0, max(0, x0 - 9), "KEY",
                       ui.color(8) | curses.A_BOLD)


KEYMAP = {
    curses.KEY_LEFT: -1, curses.KEY_RIGHT: 1,
    ord("a"): -1, ord("d"): 1, ord("A"): -1, ord("D"): 1,
}
JUMP_KEYS = {curses.KEY_UP, ord(" "), ord("w"), ord("W")}


def room_label(idx, total, st):
    if st.endless is not None:
        seed, n = st.endless
        return "RUNNER end:%d seed:%s lives:%d score:%d" % (
            n, seed, st.lives, st.score)
    return "RUNNER %d/%d lives:%d score:%d%s" % (
        idx + 1, total, st.lives, st.score,
        " KEY" if st.has_key else "")


def select_level(stdscr, score_store, progress):
    """Level-select: pick an unlocked room, or endless once unlocked."""
    total = len(LEVELS)
    unlocked = progress_mod.get_unlocked(progress, GAME_ID, total)
    endless_ok = progress_mod.endless_unlocked(progress, GAME_ID, total)
    sel = min(unlocked, total - 1)
    mode = "level"  # or "endless"
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
            ui.header(stdscr, "RUNNER: PICK A ROOM",
                      "60 rooms + endless" if endless_ok else
                      "clear rooms to unlock more")
            rows = []
            for i in range(total):
                lock = "" if i <= unlocked else " [locked]"
                rows.append("room %2d%s" % (i + 1, lock))
            if endless_ok:
                rows.append("endless mode (generated forever)")
            else:
                rows.append("endless mode [finish all 60 to unlock]")
            top = 3
            visible = max(1, h - top - 3)
            cur_idx = sel if mode == "level" else total
            start = max(0, min(cur_idx - visible // 2, len(rows) - visible))
            for i in range(start, min(len(rows), start + visible)):
                locked = (i < total and i > unlocked) or \
                         (i == total and not endless_ok)
                line = ("-> " if i == cur_idx else "   ") + rows[i]
                attr = ui.color(7) if locked else (
                    curses.A_REVERSE | curses.A_BOLD if i == cur_idx
                    else ui.color(2))
                ui.safe_addstr(stdscr, top + i - start,
                               max(2, (w - 40) // 2), line[: w - 4], attr)
            ui.footer(stdscr, "Up/Down pick | Enter play | e endless | ? help | "
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
        elif key in ui.HELP_KEYS:
            ui.show_help_overlay(stdscr, GAME_ID)
        elif key == curses.KEY_RESIZE:
            continue


def play(stdscr, score_store):
    curses.curs_set(0)
    try:
        stdscr.keypad(True)
        stdscr.timeout(90)
    except curses.error:
        pass
    if not LEVELS:
        return
    progress = progress_mod.load()
    total = len(LEVELS)
    pick = select_level(stdscr, score_store, progress)
    if pick is None:
        return
    kind, idx = pick
    if kind == "endless":
        seed = str(random.Random().randrange(1 << 30))
        endless_n = 1
        st = new_state(endless=(seed), endless_n=endless_n, seed=seed)
        level_idx = None
    else:
        st = RunState(LEVELS[idx])
        level_idx = idx
    last = time.time()
    hurt_until = 0.0  # timestamp until which "OUCH!" shows after a death
    while True:
        if ui.too_small(stdscr):
            ui.show_too_small(stdscr)
            try:
                key = stdscr.getch()
            except curses.error:
                key = -1
            if key in ui.QUIT_KEYS:
                scores_mod.record_play(score_store, GAME_ID, st.score)
                scores_mod.save(score_store)
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
                stdscr.timeout(90)
            except curses.error:
                pass
            last = time.time()
            continue
        if key in ui.HELP_KEYS:
            ui.show_help_overlay(stdscr, TITLE, CONTROLS)
            try:
                stdscr.timeout(90)
            except curses.error:
                pass
            last = time.time()
            continue
        if key == curses.KEY_RESIZE:
            continue
        if key in (ord("r"), ord("R")):
            keep_score, keep_lives = st.score, st.lives
            st = RunState(st.lv["rows"], score=keep_score,
                          endless=st.endless)
            st.lives = keep_lives
            last = time.time()
            continue
        now = time.time()
        dt = min(0.15, max(0.02, now - last))
        last = now
        move = 0
        if key in KEYMAP:
            move = KEYMAP[key]
        elif key == curses.KEY_DOWN or key in (ord("s"), ord("S")):
            move = 0
        jump = key in JUMP_KEYS or key == curses.KEY_UP
        # held-key movement: poll again without blocking for smoothness
        if st.step(dt, move=move, jump=jump) == "dead":
            hurt_until = time.time() + 1.0
        if st.over and st.won:
            if kind == "endless":
                st.score += 0
                endless_n += 1
                rows, _ = gen_endless_verified(seed, endless_n)
                keep = st.score
                lives = max(st.lives, 2)
                st = RunState(rows, score=keep,
                              endless=(seed, endless_n))
                st.lives = lives
                last = time.time()
            else:
                progress = progress_mod.load()
                progress_mod.record_level_complete(progress, GAME_ID,
                                                   level_idx, total)
                if level_idx + 1 >= total:
                    # finished everything: roll into endless
                    seed = str(random.Random().randrange(1 << 30))
                    rows, _ = gen_endless_verified(seed, 1)
                    st = RunState(rows, score=st.score, endless=(seed, 1))
                    kind = "endless"
                    endless_n = 1
                else:
                    level_idx += 1
                    st = RunState(LEVELS[level_idx], score=st.score)
                last = time.time()
        if st.over and not st.won:
            entry = scores_mod.get_entry(score_store, GAME_ID)
            _, is_high = scores_mod.record_play(score_store, GAME_ID,
                                                st.score, won=False)
            scores_mod.save(score_store)
            ui.game_over_screen(
                stdscr, TITLE,
                ["Out of lives! Rooms cleared well played."
                 if st.score else "Squished! Try room 1 again."],
                score=st.score, best=max(entry["high"], st.score),
                is_new_high=is_high, game_id=GAME_ID, won=False)
            return
        try:
            stdscr.clear()
        except curses.error:
            pass
        if kind == "endless":
            label = room_label(0, total, st)
            ouch = " OUCH! %d %s left" % (
                st.lives, "life" if st.lives == 1 else "lives") \
                if time.time() < hurt_until else ""
            draw(stdscr, st, "Generated level %d" % endless_n +
                 " | " + label + ouch)
        else:
            ouch = " OUCH! %d %s left" % (
                st.lives, "life" if st.lives == 1 else "lives") \
                if time.time() < hurt_until else ""
            draw(stdscr, st, room_label(level_idx, total, st) + ouch)
        ui.game_footer(stdscr, CONTROLS + " | room score %d" % st.score)
        try:
            stdscr.refresh()
        except curses.error:
            pass
