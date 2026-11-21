"""Hardening tests added during the v1.4.0 polish rounds (stdlib only)."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_round1_corrupt_score_entries_never_crash():
    from gamebored import scores as scores_mod
    for bad_entry in ("abc", ["hi"], None, 1e999, float("nan"),
                      {"high": "abc"}, {"high": [1]}, {"high": None},
                      {"high": 1e999}, {"plays": "x"}, {"wins": object()}):
        store = {"snake": bad_entry}
        entry = scores_mod.get_entry(store, "snake")
        assert entry == {"high": 0, "plays": 0, "wins": 0}, bad_entry
    # non-dict store itself
    assert scores_mod.get_entry(None, "snake")["high"] == 0
    assert scores_mod.get_entry(["x"], "snake")["high"] == 0
    # sane values still pass through (floats truncated like before)
    assert scores_mod.get_entry({"snake": {"high": 12, "plays": 3, "wins": 1}},
                                "snake") == {"high": 12, "plays": 3, "wins": 1}
