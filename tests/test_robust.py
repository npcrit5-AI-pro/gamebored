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


def test_round4_minesweeper_out_of_bounds_is_noop():
    from gamebored.games import minesweeper
    st = minesweeper.MineState(seed=1)
    for r, c in ((99, 99), (-1, -1), (0, 99), (99, 0)):
        st.reveal(r, c)
        st.toggle_flag(r, c)
    assert not st.over
    st.reveal(4, 4)
    assert st.started and not st.over


def test_round5_tictactoe_illegal_moves_rejected():
    from gamebored.games import tictactoe
    st = tictactoe.TicState()
    for bad in (99, -1, None, "x", 3.5):
        assert st.human(bad) is False
    assert "X" not in st.board and "O" not in st.board
    assert st.human(0) is True


def test_round6_hangman_ignores_bad_guesses():
    from gamebored.games import hangman
    st = hangman.HangState(word="APPLE")
    for bad in (None, 5, ["a"], "", "ab", "5", " "):
        assert st.guess(bad) is None
    assert st.wrong == 0 and st.guessed == set()
    assert st.guess("a") is True


def test_round7_g2048_bad_direction_and_board_are_noop():
    from gamebored.games import g2048
    board = [[2, 2, 4, 4], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]]
    new, gained, moved = g2048.move_board(board, "diagonal")
    assert new == board and gained == 0 and moved is False
    new2, _, moved2 = g2048.move_board([[2, 2], [4]], "left")
    assert moved2 is False and len(new2) == 4
    st = g2048.State2048(seed=0)
    assert st.move("diagonal") is False


def test_round8_sokoban_bad_level_clamps():
    from gamebored.games import sokoban
    for bad in (9999, -1, None, "x"):
        st = sokoban.SokState(level=bad)
        assert 0 <= st.level < len(sokoban.LEVELS)
        assert st.move(1, 0) in (True, False)
    assert sokoban.new_state(99).level == len(sokoban.LEVELS) - 1


def test_round9_safe_draw_helpers_tolerate_junk():
    from gamebored import ui as ui_mod

    class FakeWin:
        def __init__(self):
            self.calls = []

        def getmaxyx(self):
            return (24, 80)

        def addstr(self, y, x, text, attr=0):
            if not isinstance(text, str):
                raise TypeError("nope")
            self.calls.append((y, x, text))

        def addch(self, y, x, ch, attr=0):
            if isinstance(ch, int) and not 0 <= ch <= 255:
                raise ValueError("nope")
            self.calls.append((y, x, ch))

    win = FakeWin()
    ui_mod.safe_addstr(win, 0, 0, 12345)
    ui_mod.safe_addstr(win, 0, 0, None)
    ui_mod.safe_addstr(win, -5, 0, "ok")
    ui_mod.safe_addstr(win, 0, 999, "ok")
    ui_mod.safe_addch(win, 0, 0, "toolong")
    ui_mod.safe_addch(win, 0, 0, 99999)
    ui_mod.safe_addch(win, 0, 0, None)
    ui_mod.safe_addch(win, 0, 0, ord("X"))
    assert win.calls  # at least the coercible ones landed


def test_round10_search_helpers_tolerate_junk():
    from gamebored import search as search_mod
    assert search_mod.merge_results(None) == []
    assert search_mod.merge_results({"wikipedia": "junk"}) == []
    merged = search_mod.merge_results({
        "wikipedia": [None, "x", {},
                      {"title": "T", "url": "https://example.com/a"},
                      {"title": 123, "url": 456},
                      {"title": "T", "url": "https://example.com/a"}],
    })
    assert len(merged) == 2
    assert search_mod._clean(12345) == "12345"
    assert search_mod._clean(None) == ""
    res, errs = search_mod.search_all("", timeout=1)
    assert res == [] and errs == {}


def test_round11_connect4_rejects_bad_columns():
    from gamebored.games import connect4
    st = connect4.ConnectState(seed=0)
    for bad in (99, -1, None, "x", 2.5):
        assert st.drop(bad, "X") is None
    assert st.cell(99, 99) == ""
    assert st.cell("r", "c") == ""
    assert st.drop(3, "X") is not None
    # full column refuses more discs
    for _ in range(connect4.ROWS + 2):
        st.drop(0, "X")
    assert st.drop(0, "X") is None


def test_round12_frogger_tiny_dimensions_clamped():
    from gamebored.games import frogger
    for bad in (0, -3, None):
        st = frogger.FrogState(width=bad, lanes=bad, seed=0)
        assert st.width >= 4 and st.lanes >= 1
        assert st.step() is True
    st = frogger.new_state(seed=1)
    assert st.step() is True


def test_round13_wondering_detail_scroll_clamps():
    import curses
    from gamebored import wondering as wondering_mod

    class FakeWin:
        def __init__(self, keys):
            self.keys = list(keys)
            self.added = []

        def getmaxyx(self):
            return (24, 80)

        def clear(self):
            pass

        def refresh(self):
            pass

        def timeout(self, delay):
            pass

        def addstr(self, y, x, text, attr=0):
            self.added.append((y, x, text))

        def getch(self):
            if self.keys:
                return self.keys.pop(0)
            return ord("x")

    result = {"title": "T", "source": "wikipedia",
              "snippet": "short", "url": "https://example.com"}
    win = FakeWin([curses.KEY_DOWN] * 50 + [curses.KEY_UP] * 50)
    wondering_mod.show_detail(win, result)
    assert win.added
    lines = wondering_mod._detail_lines(result, 80)
    assert len(lines) <= max(1, 24 - 5) + 1


def test_round14_high_scores_scroll_clamps():
    import curses
    from gamebored import extras as extras_mod

    class FakeWin:
        def __init__(self, keys):
            self.keys = list(keys)

        def getmaxyx(self):
            return (24, 80)

        def clear(self):
            pass

        def refresh(self):
            pass

        def addstr(self, y, x, text, attr=0):
            pass

        def getch(self):
            if self.keys:
                return self.keys.pop(0)
            return ord("q")

    win = FakeWin([curses.KEY_DOWN] * 100)
    extras_mod.show_high_scores(win, {})
    win2 = FakeWin([curses.KEY_UP] * 5)
    extras_mod.show_high_scores(win2, {"snake": {"high": 9, "plays": 2}})


def test_round15_word_loader_ignores_garbage_lines(tmp_path):
    from gamebored import words as words_mod
    path = tmp_path / "words.txt"
    path.write_text("apple\n\nAVOCADO\ndon't\nx\n" + "z" * 500 + "\n  \n123\n",
                    encoding="utf-8")
    words = words_mod._read_word_file(str(path))
    assert words == ["apple", "avocado", "x"], words
    assert words_mod._read_word_file(str(tmp_path / "missing.txt")) == []


def test_round16_menu_handles_empty_entries_and_bad_keys():
    from gamebored import app as app_mod

    class FakeWin:
        def getmaxyx(self):
            return (24, 80)

        def clear(self):
            pass

        def refresh(self):
            pass

        def addstr(self, y, x, text, attr=0):
            pass

    app_mod.draw_menu(FakeWin(), 0, {}, entries=[])
    entries = app_mod.build_entries()
    assert app_mod.hotkey_index(entries, None) is None
    assert app_mod.hotkey_index(entries, "1") is None
    assert app_mod.hotkey_index(entries, -1) is None
    assert app_mod.hotkey_index(entries, 10**6) is None
    assert app_mod.hotkey_index(entries, ord("1")) is not None
    hotkeys = [e["hotkey"] for e in entries]
    assert len(set(hotkeys)) == len(hotkeys), "hotkeys must stay unique"
