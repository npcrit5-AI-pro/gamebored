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


def test_round2_atomic_save_never_leaves_half_file(tmp_path):
    import json
    from gamebored import scores as scores_mod
    path = str(tmp_path / "scores.json")
    store = {}
    scores_mod.record_play(store, "snake", 5, path=path)
    assert not os.path.exists(path + ".tmp")
    with open(path, encoding="utf-8") as fh:
        assert json.load(fh)["snake"]["high"] == 5
    # non-serializable store must not crash and must keep the old file
    scores_mod.save({"snake": object()}, path=path)
    with open(path, encoding="utf-8") as fh:
        assert json.load(fh)["snake"]["high"] == 5


def test_round3_translator_never_crashes():
    from gamebored import translator as translator_mod
    for game in ("snake", "nope", "", None):
        for raw in ("abc", None, -5, 1e18, float("nan"), float("inf"),
                    float("-inf"), "10", object()):
            assert translator_mod.to_bp(game, raw) >= 0
            assert isinstance(translator_mod.format_score(game, raw), str)
    assert translator_mod.to_bp("snake", 15) == 1500
    assert translator_mod.to_bp("nope", 15) == 0
    assert translator_mod.total_bp({"snake": {"high": "junk"}}) >= 0
