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


def _progress_dict(progress):
    return progress if isinstance(progress, dict) else {}


def _safe_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError, OverflowError):
        return default


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
        # Atomic write: a crash mid-save must never leave half a file.
        tmp_path = path + ".tmp"
        try:
            with open(tmp_path, "w", encoding="utf-8") as fh:
                json.dump(progress, fh, indent=2, sort_keys=True)
                fh.flush()
                try:
                    os.fsync(fh.fileno())
                except OSError:
                    pass
            os.replace(tmp_path, path)
        except (OSError, TypeError, ValueError):
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
    except OSError:
        pass


def get_unlocked(progress, game_id, total_levels):
    """Highest playable 0-based index for game_id (clamped to range)."""
    progress = _progress_dict(progress)
    total = _safe_int(total_levels, 1)
    if total < 1:
        total = 1
    entry = progress.get(game_id)
    if not isinstance(entry, dict):
        return 0
    unlocked = _safe_int(entry.get("unlocked", 0))
    return max(0, min(max(0, total - 1), unlocked))


def record_level_complete(progress, game_id, level, total_levels,
                          path=PROGRESS_FILE):
    """Unlock the next level after completing `level`. Returns new unlocked."""
    progress = _progress_dict(progress)
    total = _safe_int(total_levels, 1)
    if total < 1:
        total = 1
    level = _safe_int(level)
    cur = get_unlocked(progress, game_id, total)
    nxt = max(cur, min(total - 1, level + 1))
    prev = progress.get(game_id)
    prev_done = bool(isinstance(prev, dict) and prev.get("completed_all"))
    done = prev_done or level >= total - 1
    # finishing the final built-in level keeps unlocked at the last index
    # (endless unlock is derived from the completed_all flag)
    progress[game_id] = {"unlocked": nxt, "completed_all": done}
    save(progress, path)
    return nxt


def endless_unlocked(progress, game_id, total_levels):
    """True once the player has completed every built-in level."""
    progress = _progress_dict(progress)
    entry = progress.get(game_id)
    if not isinstance(entry, dict):
        return False
    return bool(entry.get("completed_all"))


def get_best(progress, game_id, key):
    """Fewest moves recorded for a room key, or None if never cleared."""
    progress = _progress_dict(progress)
    entry = progress.get(game_id)
    if not isinstance(entry, dict):
        return None
    best = entry.get("best")
    if not isinstance(best, dict):
        return None
    value = _safe_int(best.get(str(key)), -1)
    return value if value > 0 else None


def record_best(progress, game_id, key, moves, path=PROGRESS_FILE):
    """Keep the fewest moves for a room key. Returns the stored best."""
    progress = _progress_dict(progress)
    entry = progress.get(game_id)
    if not isinstance(entry, dict):
        entry = {}
        progress[game_id] = entry
    best = entry.get("best")
    if not isinstance(best, dict):
        best = {}
        entry["best"] = best
    moves = _safe_int(moves, -1)
    prev = get_best(progress, game_id, key)
    if moves > 0 and (prev is None or moves < prev):
        best[str(key)] = moves
    save(progress, path)
    return get_best(progress, game_id, key)
