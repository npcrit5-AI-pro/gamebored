"""One-off builder: emit gamebored/games/platformer_data.py with 60 levels.

Six zones of ten rooms with a gentle difficulty curve:
  1-10  flat walks, coins, tiny pits, 1-high steps
  11-20 wider pits, 2-high steps, floating platforms
  21-30 spikes (always jumpable), first patrolling enemies
  31-40 keys + locked doors, moving platforms
  41-50 combinations, longer climbs, more enemies
  51-60 hardest combos, longest rooms, everything at once

Every room is verified beatable by platformer.beatable(); the builder
refuses to write the file unless all 60 pass.

Run: python3 tools/build_platformer_data.py
"""

import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gamebored.games import platformer


def blank(W, H):
    return [[" "] * W for _ in range(H)]


def ground(g, ground, x0=0, x1=None):
    W = len(g[0])
    if x1 is None:
        x1 = W
    for x in range(x0, x1):
        for y in (ground + 1, ground + 2):
            g[y][x] = "#"


def pit(g, ground, x, w):
    for gx in range(x, x + w):
        for y in (ground + 1, ground + 2):
            g[y][gx] = " "


def coins_arc(g, ground, x, w):
    for gx in range(x, x + w):
        if 0 <= ground - 2 < len(g) and g[ground - 2][gx] == " ":
            g[ground - 2][gx] = "C"


def platform(g, x, y, w):
    for k in range(w):
        if 0 <= x + k < len(g[0]) and g[y][x + k] == " ":
            g[y][x + k] = "#"


def coin_line(g, x, y, w):
    for k in range(w):
        if 0 <= x + k < len(g[0]) and g[y][x + k] == " ":
            g[y][x + k] = "C"


def build(level, attempt=0):
    """Return grid for 1-based room number `level` (deterministic)."""
    rng = random.Random(7000 + level + attempt * 100003)
    zone = (level - 1) // 10  # 0..5
    W = min(66, 30 + level // 2 + zone * 2)
    H = 14
    ground_y = H - 3
    g = blank(W, H)
    for y in range(H):
        g[y][0] = "#"
        g[y][W - 1] = "#"
    ground(g, ground_y)
    g[H - 1] = ["#"] * W
    reserved = set()  # columns kept pit-free (moving-platform crossings)

    # --- moving platform over a wide pit (zone 3+): placed first ---
    if zone >= 3 and rng.random() < 0.8:
        m_cands = list(range(8, max(9, W - 14)))
        if m_cands:
            mx = rng.choice(m_cands)
            pit(g, ground_y, mx - 1, 7)
            coins_arc(g, ground_y, mx - 1, 7)
            for k in range(3):
                g[ground_y - 1][mx + k] = "M"
            reserved.update(range(mx - 3, mx + 9))

    # --- pits (gaps in the ground), width grows with zone ---
    max_gap = [2, 3, 3, 4, 4, 4][zone]
    npits = [1, 1, 2, 2, 3, 3][zone] + (1 if level % 3 == 0 else 0)
    x = 7
    for _ in range(npits):
        if x > W - 12:
            break
        w = rng.choice(list(range(2, max_gap + 1)))
        if any(c in reserved for c in range(x, x + w)):
            x += w + rng.randrange(4, 8)
            continue
        pit(g, ground_y, x, w)
        if rng.random() < 0.8:
            coins_arc(g, ground_y, x, w)
        x += w + rng.randrange(4, 8)

    # --- floating platforms (higher zones: taller, longer chains) ---
    nplat = [1, 2, 2, 3, 4, 5][zone]
    for _ in range(nplat):
        px = rng.randrange(4, max(5, W - 10))
        py = rng.randrange(max(2, ground_y - 3 - zone), ground_y - 1)
        w = rng.choice([3, 3, 4, 4, 5])
        platform(g, px, py, w)
        if rng.random() < 0.85:
            coin_line(g, px, py - 1, w)

    # --- 1-2 high steps (stairs need a floor underneath) ---
    if zone >= 1 and W > 20:
        for _try in range(6):
            sx = rng.randrange(5, W - 12)
            if any(c in reserved for c in range(sx, sx + 3)):
                continue
            if any(g[ground_y + 1][sx + k] != "#" for k in range(3)):
                continue
            if any(g[ground_y][sx + k] != " " for k in range(3)):
                continue
            step_h = 1 if zone < 2 and rng.random() < 0.6 else 2
            # build a staircase of blocks
            for k in range(3):
                hgt = step_h if k == 1 else 1
                for y in range(ground_y - hgt, ground_y):
                    if 0 < sx + k < W - 1 and g[y][sx + k] == " ":
                        g[y][sx + k] = "#"
            break

    # --- spikes (zone 2+, always single/double on flat ground) ---
    if zone >= 2:
        nsp = [0, 0, 2, 2, 3, 4][zone]
        for _ in range(nsp):
            sx = rng.randrange(5, W - 5)
            if g[ground_y][sx] == " " and g[ground_y + 1][sx] == "#":
                g[ground_y][sx] = "^"
                if zone >= 4 and rng.random() < 0.35 and \
                        g[ground_y][sx + 1] == " " and \
                        g[ground_y + 1][sx + 1] == "#":
                    g[ground_y][sx + 1] = "^"

    # --- enemies (zone 2+, more later) ---
    if zone >= 2:
        nen = [0, 0, 1, 2, 2, 3][zone]
        for _ in range(nen):
            ex = rng.randrange(5, W - 5)
            if g[ground_y][ex] == " " and g[ground_y + 1][ex] == "#":
                g[ground_y][ex] = "E"

    # --- key + locked door (zone 3+: door needs a floor, key on ground) ---
    if zone >= 3:
        cands = [dx for dx in range(max(12, W - 16), W - 6)
                 if g[ground_y + 1][dx] == "#" and g[ground_y][dx] == " "
                 and g[ground_y - 1][dx] == " "]
        if cands:
            dx = rng.choice(cands)
            for y in (ground_y - 1, ground_y):
                g[y][dx] = "D"
            key_spots = [kx for kx in range(3, max(4, dx - 2))
                         if g[ground_y][kx] == " "
                         and g[ground_y + 1][kx] == "#"]
            if key_spots:
                kx = rng.choice(key_spots)
                g[ground_y][kx] = "K"

    # --- moving platform over a wide pit (zone 3+): placed first ---
    # (see above; nothing to do here)

    # --- zone 5-6 garnish: extra enemy on a platform, extra spikes ---
    if zone >= 4:
        ex = rng.randrange(6, W - 6)
        for y in range(2, ground_y):
            if g[y][ex] == "#" and g[y - 1][ex] == " ":
                g[y - 1][ex] = "E"
                break

    # spawn + exit (keep surroundings clear)
    g[ground_y][1] = "P"
    if g[ground_y][2] == "^":
        g[ground_y][2] = " "
    ex = W - 2
    g[ground_y][ex] = "X"
    if g[ground_y][ex - 1] == "^":
        g[ground_y][ex - 1] = " "
    for y in (ground_y - 1, ground_y - 2):
        if g[y][ex] == "#":
            g[y][ex] = " "
    return tuple("".join(r).rstrip() for r in g)


def main():
    levels = []
    bad = []
    for lv in range(1, 61):
        rows = None
        for attempt in range(80):
            cand = build(lv, attempt)
            if platformer.beatable(cand):
                rows = cand
                break
        if rows is None:
            bad.append(lv)
            rows = build(lv)
        levels.append(rows)
    print("built 60 rooms, unbeatable: %s" % bad)
    if bad:
        print("REFUSING to write: fix zones %s first" % bad)
        sys.exit(1)
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(os.path.dirname(here), "gamebored", "games",
                       "platformer_data.py")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write('"""Runner built-in rooms (60, difficulty curve zones 1-6).\n\n')
        fh.write('Generated once by tools/build_platformer_data.py with fixed\n')
        fh.write('seeds and verified beatable by the reachability solver.\n')
        fh.write('"""\n\nLEVELS = (\n')
        for rows in levels:
            fh.write("    (\n")
            for r in rows:
                fh.write("        %r,\n" % r)
            fh.write("    ),\n")
        fh.write(")\n")
    print("wrote %s" % out)


if __name__ == "__main__":
    main()
