"""High-score persistence for GameBored.

Scores live in ~/.local/share/gamebored/scores.json so they survive upgrades.
Only the standard library is used.
"""

import json
import os

APP_DIR = os.path.join(os.path.expanduser("~"), ".local", "share", "gamebored")
SCORES_FILE = os.path.join(APP_DIR, "scores.json")


def _ensure_dir():
    try:
        os.makedirs(APP_DIR, exist_ok=True)
    except OSError:
        pass


def load(path=SCORES_FILE):
    """Return the scores dict {game_id: {"high": int, "plays": int, "wins": int}}."""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
            if isinstance(data, dict):
                return data
    except (OSError, ValueError):
        pass
    return {}


def save(scores, path=SCORES_FILE):
    _ensure_dir() if path == SCORES_FILE else None
    try:
        if path != SCORES_FILE:
            parent = os.path.dirname(path)
            if parent:
                os.makedirs(parent, exist_ok=True)
        else:
            _ensure_dir()
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(scores, fh, indent=2, sort_keys=True)
    except OSError:
        pass


def _safe_int(value):
    """Coerce anything to a non-negative int; never raises."""
    try:
        value = int(value)
    except (TypeError, ValueError, OverflowError):
        return 0
    if value != value:  # NaN guard (int(float('nan')) raises, but be safe)
        return 0
    return max(0, value)


def get_entry(scores, game_id):
    entry = scores.get(game_id) if isinstance(scores, dict) else None
    if not isinstance(entry, dict):
        return {"high": 0, "plays": 0, "wins": 0}
    return {
        "high": _safe_int(entry.get("high", 0) or 0),
        "plays": _safe_int(entry.get("plays", 0) or 0),
        "wins": _safe_int(entry.get("wins", 0) or 0),
    }


def record_play(scores, game_id, score=0, won=False, path=SCORES_FILE):
    """Record one finished game. Returns (entry, is_new_high)."""
    entry = get_entry(scores, game_id)
    entry["plays"] += 1
    if won:
        entry["wins"] += 1
    is_new_high = False
    try:
        score = int(score)
    except (TypeError, ValueError):
        score = 0
    if score > entry["high"]:
        entry["high"] = score
        is_new_high = True
    scores[game_id] = entry
    save(scores, path)
    return entry, is_new_high
