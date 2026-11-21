"""One-off builder: emit gamebored/games/sokoban_data.py with 200+ levels.

Sources:
- 3 original GameBored rooms (kept first, tutorial-easy).
- Microban by David W. Skinner (freely redistributable with credit):
  the subset that our push-solver proves solvable within a generous budget
  (these are published, known-solvable puzzles; we re-verify each one).
- GameBored extras: tiny reverse-pulled rooms (seeded, frozen as strings).

Run: python3 tools/build_sokoban_data.py  (writes gamebored/games/sokoban_data.py)
"""

import os
import random
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gamebored.games import sokoban_solver as solver

ORIGINAL = [
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
]

DIRS = ((0, -1), (0, 1), (-1, 0), (1, 0))


def reverse_pull_level(rng, width=8, height=7, nboxes=2, pulls=25,
                       pillars=0):
    """Scramble a solved open room with reverse pulls. Always solvable."""
    W, H = width, height
    walls = set()
    for x in range(W):
        walls.add((x, 0))
        walls.add((x, H - 1))
    for y in range(H):
        walls.add((0, y))
        walls.add((W - 1, y))
    # random interior pillars (keep border-adjacent free-ish)
    for _ in range(pillars):
        x = rng.randrange(2, W - 2)
        y = rng.randrange(2, H - 2)
        walls.add((x, y))
    floors = [(x, y) for y in range(1, H - 1) for x in range(1, W - 1)
              if (x, y) not in walls]
    if len(floors) < 2 * nboxes + 2:
        return None
    targets = set(rng.sample(floors, nboxes))
    boxes = set(targets)
    free = [c for c in floors if c not in boxes]
    player = rng.choice(free)

    def free_cell(c):
        return c not in walls and c not in boxes

    for _ in range(pulls):
        if rng.random() < 0.45:
            # reverse pull: box adjacent to player, cell behind player free
            cands = []
            for dx, dy in DIRS:
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
        # ordinary reverse walk
        opts = []
        for dx, dy in DIRS:
            n = (player[0] + dx, player[1] + dy)
            if n not in walls and n not in boxes:
                opts.append(n)
        if opts:
            player = rng.choice(opts)
    if not boxes or frozenset(boxes) <= targets:
        return None
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


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    repo = os.path.dirname(here)
    src = os.path.join("/tmp", "microban.js")
    if not os.path.exists(src):
        # fallback: try next to the script
        src = os.path.join(here, "microban.js")
    txt = open(src, encoding="utf-8").read()
    micro = re.findall(r"`(.*?)`", txt, re.S)
    print("microban found: %d" % len(micro))

    picked = []
    for i, lv in enumerate(micro):
        rows = tuple(lv.split("\n"))
        if not rows:
            continue
        sol = solver.solve_pushes(rows, cap=30000, time_limit=3.0)
        if sol is not None:
            picked.append((i, rows, len(sol)))
    print("microban solvable within budget: %d" % len(picked))

    # GameBored extras via reverse pulls (frozen strings, solver-verified)
    extras = []
    rng = random.Random(20261121)
    cfg = 0
    attempt = 0
    while len(extras) < 95 and attempt < 6000:
        attempt += 1
        w = rng.choice([7, 8, 8, 9, 9, 10])
        h = rng.choice([6, 7, 7, 8])
        nb = rng.choice([1, 2, 2, 2, 3, 3])
        pulls = rng.randrange(12, 45)
        pillars = rng.choice([0, 0, 0, 1, 1, 2])
        rows = reverse_pull_level(random.Random(rng.randrange(1 << 30)),
                                  width=w, height=h, nboxes=nb,
                                  pulls=pulls, pillars=pillars)
        if not rows:
            continue
        if rows in extras:
            continue
        if solver.solve_pushes(rows, cap=20000, time_limit=2.0) is None:
            continue
        extras.append(rows)
    print("extras generated: %d" % len(extras))

    levels = list(ORIGINAL) + [r for _, r, _ in picked] + extras
    print("total: %d" % len(levels))

    out = os.path.join(repo, "gamebored", "games", "sokoban_data.py")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write('"""Sokoban level collection (built-in rooms).\n\n')
        fh.write('3 original GameBored tutorial rooms, then a curated subset of\n')
        fh.write('Microban by David W. Skinner (freely redistributable with\n')
        fh.write('credit; see README), then GameBored reverse-pulled extras.\n')
        fh.write('Every room is verified solvable by the push-solver in tests.\n')
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
