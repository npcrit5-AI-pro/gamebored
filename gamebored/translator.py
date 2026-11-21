"""Score Translator: one universal unit for all GameBored scores.

Every game keeps its own natural raw score (Snake counts apples, 2048
counts merges, Tic-Tac-Toe counts wins, ...). Those numbers live on wildly
different scales, so this module translates each of them into a single
shared language: Bored Points (BP).

The rule is simple on purpose: BP = raw * RATE, where RATE is a
per-game conversion rate calibrated so that a comparable effort in any
game earns a comparable pile of BP (a decent few minutes of play lands
around 1,000-1,500 BP in every game). Only the standard library is used.
"""

UNIT_NAME = "Bored Points"
UNIT_SYMBOL = "BP"

# Per-game conversion rates: BP = raw * RATE.
# "raw" is each game's natural score (see the "Raw score" column), and
# "typical" is what a decent casual session earns, mapping to ~1,000-1,500 BP.
CONVERSIONS = {
    # --- the original ten ---
    "snake": {"rate": 100, "raw": "apples eaten",
              "example": "15 apples -> 1,500 BP"},
    "tetris": {"rate": 3, "raw": "stack points (40/line, +2/piece)",
               "example": "500 pts -> 1,500 BP"},
    "g2048": {"rate": 0.3, "raw": "merge points",
              "example": "5,000 pts -> 1,500 BP"},
    "minesweeper": {"rate": 1.5, "raw": "clear points (win ~= 500-1,500)",
                    "example": "1,000 pts -> 1,500 BP"},
    "tictactoe": {"rate": 15, "raw": "100 win / 10 draw / 0 loss",
                  "example": "win (100) -> 1,500 BP"},
    "hangman": {"rate": 15, "raw": "word points (~50-160 per win)",
                "example": "100 pts -> 1,500 BP"},
    "pong": {"rate": 7.5, "raw": "match points (win = 200)",
             "example": "win (200) -> 1,500 BP"},
    "invaders": {"rate": 3, "raw": "alien points (10 x level each)",
                 "example": "500 pts -> 1,500 BP"},
    "breakout": {"rate": 3, "raw": "brick points + 200 win bonus",
                 "example": "500 pts -> 1,500 BP"},
    "wordle": {"rate": 12.5, "raw": "guess points (20-120 per win)",
               "example": "80 pts -> 1,000 BP"},
    # --- the five new games ---
    "frogger": {"rate": 4, "raw": "crossing points (100 per crossing)",
                "example": "400 pts -> 1,600 BP"},
    "simon": {"rate": 150, "raw": "rounds cleared (best streak)",
              "example": "10 rounds -> 1,500 BP"},
    "sokoban": {"rate": 2, "raw": "box points (100/box + 500/level)",
                "example": "800 pts -> 1,600 BP"},
    "connect4": {"rate": 10, "raw": "150 win / 25 draw / 0 loss",
                 "example": "win (150) -> 1,500 BP"},
    "flappy": {"rate": 100, "raw": "pipes passed",
               "example": "15 pipes -> 1,500 BP"},
    "platformer": {"rate": 2, "raw": "room points (200/room + 10/coin)",
                   "example": "750 pts -> 1,500 BP"},
}


def rate_for(game_id):
    """Return the BP-per-raw rate for a game (0.0 for unknown games)."""
    info = CONVERSIONS.get(game_id)
    if not info:
        return 0.0
    try:
        return float(info["rate"])
    except (TypeError, ValueError):
        return 0.0


def to_bp(game_id, raw):
    """Translate a raw score into Bored Points (int, never negative)."""
    try:
        raw = float(raw)
    except (TypeError, ValueError):
        return 0
    if raw <= 0:
        return 0
    return int(round(raw * rate_for(game_id)))


def _commas(n):
    try:
        n = int(n)
    except (TypeError, ValueError):
        return "0"
    # thousands separators without locale dependency
    s = "%d" % n
    out = ""
    while len(s) > 3:
        out = "," + s[-3:] + out
        s = s[:-3]
    return s + out


def format_score(game_id, raw):
    """Return '1,240 -> 1,240 BP'-style text for a raw score."""
    return "%s -> %s %s" % (_commas(raw), _commas(to_bp(game_id, raw)),
                            UNIT_SYMBOL)


def total_bp(score_store):
    """Combined BP across every game's stored high score."""
    from . import scores as scores_mod
    total = 0
    for game_id in CONVERSIONS:
        total += to_bp(game_id, scores_mod.get_entry(score_store, game_id)["high"])
    return total
