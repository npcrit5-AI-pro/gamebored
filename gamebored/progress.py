"""Saved progress for level-based games (platformer, sokoban).

Progress lives in ~/.local/share/gamebored/progress.json so it survives
upgrades and reinstalls of the code. Only the standard library is used.

Stored shape: {"platformer": {"unlocked": int}, "sokoban": {"unlocked": int}}
where "unlocked" is the highest 0-based level index the player may start.
Level 0 is always unlocked. Completing level k unlocks k+1 (clamped).
Endless mode unlocks once every built-in level is complete.
"""

import json
import os

from . import scores as scores_mod

PROGRESS_FILE = os.path.join(scores_mod.APP_DIR, "progress.json")


def load(path=PROGRESS_FILE):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
            if isinstance(data, dict):
                return data
    except (OSError, ValueError):
        pass
    return {}


def save(progress, path=PROGRESS_FILE):
    try:
        if path == PROGRESS_FILE:
            scores_mod._ensure_dir()
        else:
            parent = os.path.dirname(path)
            if parent:
                os.makedirs(parent, exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(progress, fh, indent=2, sort_keys=True)
    except OSError:
        pass


def get_unlocked(progress, game_id, total_levels):
    """Highest playable 0-based index for game_id (clamped to range)."""
    try:
        total = int(total_levels)
    except (TypeError, ValueError):
        total = 1
    entry = progress.get(game_id)
    if not isinstance(entry, dict):
        return 0
    try:
        unlocked = int(entry.get("unlocked", 0))
    except (TypeError, ValueError):
        unlocked = 0
    return max(0, min(max(0, total - 1), unlocked))


def record_level_complete(progress, game_id, level, total_levels,
                          path=PROGRESS_FILE):
    """Unlock the next level after completing `level`. Returns new unlocked."""
    try:
        total = int(total_levels)
    except (TypeError, ValueError):
        total = 1
    cur = get_unlocked(progress, game_id, total)
    nxt = max(cur, min(total - 1, int(level) + 1))
    # finishing the final built-in level keeps unlocked at the last index
    # (endless unlock is derived from unlocked == total - 1 + completed flag)
    progress[game_id] = {"unlocked": nxt,
                         "completed_all": bool(progress.get(game_id, {}).get(
                             "completed_all", False) or
                             int(level) >= total - 1)}
    if int(level) >= total - 1:
        progress[game_id]["completed_all"] = True
    save(progress, path)
    return nxt


def endless_unlocked(progress, game_id, total_levels):
    """True once the player has completed every built-in level."""
    entry = progress.get(game_id)
    if not isinstance(entry, dict):
        return False
    if entry.get("completed_all"):
        return True
    try:
        return int(entry.get("unlocked", 0)) >= int(total_levels) - 1 and \
            bool(entry.get("completed_all", False))
    except (TypeError, ValueError):
        return False
