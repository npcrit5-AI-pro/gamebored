"""Unit tests for the Score Translator (Bored Points)."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gamebored import translator
from gamebored.games import GAMES


# A decent casual session in each game; every one of these should land in
# roughly the same BP neighbourhood (calibration requirement).
TYPICAL_GOOD_RAW = {
    "snake": 15,        # 15 apples
    "tetris": 500,      # a few lines + pieces
    "g2048": 5000,      # mid-game merge score
    "minesweeper": 1000,  # a solid win
    "tictactoe": 100,   # one win
    "hangman": 100,     # a good word save
    "pong": 200,        # match win vs CPU
    "invaders": 500,    # a wave and a half
    "breakout": 500,    # most bricks + bonus
    "wordle": 80,       # a clean solve
    "frogger": 400,     # 4 crossings
    "simon": 10,        # 10 rounds remembered
    "sokoban": 800,     # a room or two
    "connect4": 150,    # one win
    "flappy": 15,       # 15 pipes threaded
}


class TestTranslator(unittest.TestCase):
    def test_unit_name_and_symbol(self):
        self.assertEqual(translator.UNIT_NAME, "Bored Points")
        self.assertEqual(translator.UNIT_SYMBOL, "BP")

    def test_every_game_has_a_positive_rate(self):
        game_ids = [mod.GAME_ID for mod in GAMES]
        self.assertEqual(len(game_ids), 15)
        for gid in game_ids:
            self.assertIn(gid, translator.CONVERSIONS,
                          "no conversion rate for %s" % gid)
            self.assertGreater(translator.rate_for(gid), 0,
                               "non-positive rate for %s" % gid)

    def test_known_conversions(self):
        self.assertEqual(translator.to_bp("snake", 15), 1500)
        self.assertEqual(translator.to_bp("flappy", 15), 1500)
        self.assertEqual(translator.to_bp("simon", 10), 1500)
        self.assertEqual(translator.to_bp("g2048", 5000), 1500)
        self.assertEqual(translator.to_bp("tictactoe", 100), 1500)
        self.assertEqual(translator.to_bp("connect4", 150), 1500)

    def test_calibration_comparable_effort_comparable_bp(self):
        for gid, raw in TYPICAL_GOOD_RAW.items():
            bp = translator.to_bp(gid, raw)
            self.assertGreaterEqual(bp, 700,
                                    "%s: %r raw -> %d BP (too low)" %
                                    (gid, raw, bp))
            self.assertLessEqual(bp, 2500,
                                 "%s: %r raw -> %d BP (too high)" %
                                 (gid, raw, bp))

    def test_monotonic(self):
        for gid in translator.CONVERSIONS:
            self.assertLessEqual(translator.to_bp(gid, 0),
                                 translator.to_bp(gid, 10))
            self.assertLessEqual(translator.to_bp(gid, 10),
                                 translator.to_bp(gid, 1000))

    def test_bad_inputs_give_zero(self):
        self.assertEqual(translator.to_bp("snake", 0), 0)
        self.assertEqual(translator.to_bp("snake", -50), 0)
        self.assertEqual(translator.to_bp("snake", "junk"), 0)
        self.assertEqual(translator.to_bp("snake", None), 0)
        self.assertEqual(translator.to_bp("no-such-game", 100), 0)

    def test_format_score(self):
        text = translator.format_score("snake", 248)
        self.assertIn("248", text)
        self.assertIn("->", text)
        self.assertIn("BP", text)
        self.assertIn("24,800", text)  # thousands separator
        # unknown games still render without crashing
        self.assertIn("BP", translator.format_score("nope", 5))

    def test_total_bp_sums_highs(self):
        store = {"snake": {"high": 15, "plays": 1, "wins": 0},
                 "flappy": {"high": 10, "plays": 1, "wins": 0}}
        self.assertEqual(store and translator.total_bp(store), 1500 + 1000)
        self.assertEqual(translator.total_bp({}), 0)


if __name__ == "__main__":
    unittest.main()
