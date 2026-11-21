"""Fast push-based Sokoban solver with corner-deadlock pruning.

Used by the game (to verify procedurally generated endless levels) and by
the test suite (to prove every built-in level is solvable). Move-based BFS
explodes on anything beyond a closet; push-based search (player reachability
+ box pushes) solves small rooms in milliseconds.

Only the standard library is used.
"""

from collections import deque
import time

DIRS = ((0, -1), (0, 1), (-1, 0), (1, 0))


def parse(rows):
    """Parse XSB-ish rows. Returns (walls, targets, boxes, player, W, H)."""
    H = len(rows)
    W = max((len(r) for r in rows), default=0)
    rows = [r.ljust(W) for r in rows]
    walls, targets, boxes = set(), set(), set()
    player = None
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch == "#":
                walls.add((x, y))
            elif ch == ".":
                targets.add((x, y))
            elif ch == "$":
                boxes.add((x, y))
            elif ch == "*":
                boxes.add((x, y))
                targets.add((x, y))
            elif ch == "@":
                if player is None:
                    player = (x, y)
            elif ch == "+":
                if player is None:
                    player = (x, y)
                targets.add((x, y))
            # ' ', '_', '-', floor chars: empty floor
    return walls, targets, boxes, player, W, H


def reachable(walls, boxes, start):
    """Flood-fill of squares the player can walk to (boxes are obstacles)."""
    seen = {start}
    queue = deque([start])
    while queue:
        x, y = queue.popleft()
        for dx, dy in DIRS:
            n = (x + dx, y + dy)
            if n in walls or n in boxes or n in seen:
                continue
            seen.add(n)
            queue.append(n)
    return seen


def _corner_dead(walls, targets, pos):
    if pos in targets:
        return False
    x, y = pos
    return ((x - 1, y) in walls or (x + 1, y) in walls) and \
           ((x, y - 1) in walls or (x, y + 1) in walls)


def solve_pushes(rows, cap=20000, time_limit=2.0):
    """Push-based BFS. Returns list of pushes [(dx,dy),...] or None.

    `cap` bounds explored push-states; `time_limit` bounds seconds.
    Levels needing more than the budget return None (caller may fall back
    to a stored-solution replay for big handcrafted rooms).
    """
    walls, targets, boxes, player, _, _ = parse(rows)
    if player is None or not boxes:
        return None
    if frozenset(boxes) <= targets:
        return []
    t0 = time.time()
    start_boxes = frozenset(boxes)
    seen = {(player, start_boxes)}
    queue = deque([(player, start_boxes, [])])
    while queue:
        if len(seen) >= cap or (time.time() - t0) > time_limit:
            return None
        p, bset, path = queue.popleft()
        if bset <= targets:
            return path
        bset_s = set(bset)
        reach = reachable(walls, bset_s, p)
        for b in bset:
            bx, by = b
            for dx, dy in DIRS:
                frm = (bx - dx, by - dy)
                to = (bx + dx, by + dy)
                if frm not in reach:
                    continue
                if to in walls or to in bset_s:
                    continue
                if _corner_dead(walls, targets, to):
                    continue
                nb = frozenset(to if q == b else q for q in bset)
                key = (b, nb)
                if key not in seen:
                    seen.add(key)
                    queue.append((b, nb, path + [(dx, dy)]))
    return None


def solvable(rows, cap=20000, time_limit=2.0):
    return solve_pushes(rows, cap=cap, time_limit=time_limit) is not None


def verify_replay(rows, moves):
    """Replay a stored move list (dx,dy steps); True if it solves the room."""
    walls, targets, boxes, player, _, _ = parse(rows)
    if player is None:
        return False
    boxes = set(boxes)
    px, py = player
    for mv in moves:
        try:
            dx, dy = mv
        except (TypeError, ValueError):
            return False
        nx, ny = px + dx, py + dy
        if (nx, ny) in walls:
            return False
        if (nx, ny) in boxes:
            bx, by = nx + dx, ny + dy
            if (bx, by) in walls or (bx, by) in boxes:
                return False
            boxes.discard((nx, ny))
            boxes.add((bx, by))
        px, py = nx, ny
    return bool(boxes) and frozenset(boxes) <= targets
