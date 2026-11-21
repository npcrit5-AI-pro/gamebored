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
    assert len(sokoban.LEVELS) == 205  # v1.3.0's full room set is intact
    assert sokoban.new_state(9999).level == len(sokoban.LEVELS) - 1
    assert sokoban.new_state(-5).level == 0


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


def test_round18_snake_rejects_bad_dimensions_and_turns():
    from gamebored.games import snake
    for bad in (0, -5, None):
        st = snake.new_state(bad, bad, seed=1)
        assert st.width >= 4 and st.height >= 4
        assert st.step() in (True, False)
    st = snake.new_state(6, 6, seed=1)
    before = st.pending
    for bad in (None, 5, "up", (9, 9), (0, 0)):
        st.set_direction(bad)
    assert st.pending == before
    st.set_direction(snake.UP)
    assert st.pending == snake.UP


def test_round19_flappy_clamps_bad_dimensions():
    from gamebored.games import flappy
    for bad in (0, -4, None):
        st = flappy.FlapState(width=bad, height=bad, seed=0)
        assert st.width >= 12 and st.height >= 8
        assert st.step(True) in (True, False)
    st = flappy.FlapState(width=40, height=16, gap=999, seed=0)
    assert st.gap <= st.height - 2


def test_round21_menu_subtitle_tracks_package_version():
    from gamebored import __version__, app as app_mod
    assert __version__ in app_mod.SUBTITLE
    assert "1.2.0" not in app_mod.SUBTITLE or __version__ == "1.2.0"


def test_round22_cli_flags_do_not_launch_curses(capsys):
    from gamebored import __main__ as main_mod
    assert main_mod.main(["--help"]) == 0
    assert main_mod.main(["-h"]) == 0
    assert main_mod.main(["--version"]) == 0
    out = capsys.readouterr().out
    assert "GameBored" in out
    assert main_mod.main(["--list"]) == 0
    assert "Snake" in capsys.readouterr().out
    assert main_mod.main(["--bogus"]) == 2
    assert "Usage" in capsys.readouterr().out


def test_round23_word_answers_normalized():
    from gamebored.games import hangman, wordle
    st = hangman.HangState(word="apple")
    assert st.word == "APPLE"
    assert st.guess("a") is True
    st2 = hangman.HangState(word="123")
    assert st2.word.isalpha() and st2.word.isupper()
    st3 = hangman.HangState(word=None, seed=1)
    assert st3.word.isupper()
    w = wordle.WordleState(answer="crane")
    assert w.answer == "CRANE"
    w2 = wordle.WordleState(answer="toolongword")
    assert len(w2.answer) == wordle.WORD_LEN
    w3 = wordle.WordleState(answer="CRANE")
    for ch in "CRANE":
        w3.type_letter(ch)
    assert w3.submit() is True and w3.won


def test_round28_menu_restores_hidden_cursor(monkeypatch):
    from gamebored import app as app_mod
    calls = []
    monkeypatch.setattr("curses.curs_set", lambda n: calls.append(n))

    class FakeWin:
        def keypad(self, flag):
            pass

        def timeout(self, delay):
            pass

    app_mod._hide_cursor(FakeWin())
    assert calls == [0]


def test_round30_menu_loop_survives_empty_registry(monkeypatch):
    import curses
    from gamebored import app as app_mod
    monkeypatch.setattr(app_mod, "build_entries", lambda: [])

    class FakeWin:
        def __init__(self):
            self.keys = [ord("q")]

        def getmaxyx(self):
            return (24, 80)

        def clear(self):
            pass

        def refresh(self):
            pass

        def keypad(self, flag):
            pass

        def timeout(self, delay):
            pass

        def addstr(self, y, x, text, attr=0):
            pass

        def getch(self):
            return self.keys.pop(0) if self.keys else ord("q")

    app_mod.menu_loop(FakeWin())  # must return, not raise


def test_round33_every_draw_survives_odd_sizes():
    import sys
    sys.path.insert(0, os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "tools"))
    from capture import FakeScreen
    from gamebored.games import (snake, tetris, g2048, minesweeper, tictactoe,
                                 hangman, pong, invaders, breakout, wordle,
                                 frogger, simon, sokoban, connect4, flappy,
                                 platformer)
    cases = [
        lambda s: snake.draw(s, snake.SnakeState(20, 14, seed=7)),
        lambda s: tetris.draw(s, tetris.TetrisState(seed=1)),
        lambda s: g2048.draw(s, g2048.State2048(seed=1)),
        lambda s: minesweeper.draw(s, minesweeper.MineState(seed=9), (0, 0)),
        lambda s: tictactoe.draw(s, tictactoe.TicState()),
        lambda s: hangman.draw(s, hangman.HangState(word="PYTHON")),
        lambda s: pong.draw(s, pong.PongState(width=60, height=18), 10, 3),
        lambda s: invaders.draw(s, invaders.InvaderState(50, 16, seed=2),
                                15, 4),
        lambda s: breakout.draw(s, breakout.BreakState(50, 16), 15, 4),
        lambda s: wordle.draw(s, wordle.WordleState(answer="CRANE")),
        lambda s: frogger.draw(s, frogger.new_state(seed=7)),
        lambda s: simon.draw(s, simon.new_state(seed=3)),
        lambda s: sokoban.draw(s, sokoban.new_state(1), 0),
        lambda s: connect4.draw(s, connect4.new_state(seed=1)),
        lambda s: flappy.draw(s, flappy.new_state(seed=2)),
        lambda s: platformer.draw(
            s, platformer.RunState(platformer.LEVELS[12]),
            platformer.room_label(12, len(platformer.LEVELS),
                                  platformer.RunState(platformer.LEVELS[12]))),
    ]
    assert len(cases) == 16
    for draw in cases:
        for w, h in ((80, 24), (79, 23), (40, 10), (20, 6), (200, 60)):
            draw(FakeScreen(h, w))  # must not raise


def test_round34_capture_renders_every_screen(tmp_path):
    import sys
    sys.path.insert(0, os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "tools"))
    from capture import build_states
    states = build_states()
    assert len(states) == 16 + 3, sorted(states)
    for name, text in states.items():
        assert isinstance(text, str) and text.strip(), name


def test_round35_corrupt_progress_json_never_crashes(tmp_path):
    import json
    from gamebored import progress as progress_mod
    path = str(tmp_path / "progress.json")
    # missing file -> empty progress, level 0 unlocked, endless locked
    assert progress_mod.load(path) == {}
    assert progress_mod.get_unlocked({}, "sokoban", 205) == 0
    assert not progress_mod.endless_unlocked({}, "sokoban", 205)
    # corrupt file shapes -> empty, never raise
    for bad in ('not json{{{', '[1, 2]', '"str"', 'null'):
        with open(path, "w") as fh:
            fh.write(bad)
        assert progress_mod.load(path) == {}, bad
    # valid JSON with junk values loads but reads as locked/zero
    for bad in ('{"sokoban": "junk"}',
                '{"sokoban": {"unlocked": "abc"}}',
                '{"platformer": [1]}'):
        with open(path, "w") as fh:
            fh.write(bad)
        store = progress_mod.load(path)
        assert progress_mod.get_unlocked(store, "sokoban", 205) == 0
        assert not progress_mod.endless_unlocked(store, "sokoban", 205)
    # non-dict stores and junk levels never raise
    for bad_store in (["x"], "str", None, 42,
                      {"sokoban": [1]}, {"platformer": None}):
        assert progress_mod.get_unlocked(bad_store, "sokoban", 205) == 0
        assert not progress_mod.endless_unlocked(bad_store, "sokoban", 205)
    for bad_level in ("x", None, [1], -5):
        nxt = progress_mod.record_level_complete({}, "sokoban", bad_level,
                                                 205, path=path)
        # junk coerces to level <= 0: can never skip ahead, never raises
        assert nxt <= 1, bad_level
    # normal flow still unlocks and persists
    store = {}
    assert progress_mod.record_level_complete(store, "sokoban", 0, 205,
                                              path=path) == 1
    assert json.load(open(path))["sokoban"]["unlocked"] == 1
    # atomic save: junk never corrupts the file on disk
    progress_mod.save({"sokoban": object()}, path=path)
    assert json.load(open(path))["sokoban"]["unlocked"] == 1
    assert not os.path.exists(path + ".tmp")


def test_round36_runner_ignores_junk_input():
    from gamebored.games import platformer
    assert len(platformer.LEVELS) == 60  # v1.3.0's 60 rooms are intact
    st = platformer.RunState(platformer.LEVELS[0])
    for bad_dt in ("x", None, [1], float("nan"), float("inf")):
        st.step(bad_dt)  # must not raise
    for bad_move in ("x", None, [1], float("nan")):
        st.step(0.09, move=bad_move)  # must not raise
    for bad_rows in (None, 42):
        st2 = platformer.RunState(bad_rows)
        st2.step(0.09, move=1)
    assert platformer.new_state(level=9999).step(0.09) in \
        ("dead", "won", "over", None)
    assert platformer.new_state(level=-5).step(0.09) in \
        ("dead", "won", "over", None)
    assert platformer.new_state(level="x").step(0.09) in \
        ("dead", "won", "over", None)


def test_round37_room_pickers_survive_key_mashing():
    import curses
    from gamebored.games import sokoban, platformer

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
            return self.keys.pop(0) if self.keys else ord("q")

    mash = ([curses.KEY_DOWN] * 300 + [curses.KEY_UP] * 300
            + [ord("e"), 10])
    for progress in ({}, {"sokoban": "junk"}, {"platformer": {"unlocked":
                                                              "abc"}},
                     {"sokoban": {"unlocked": 204,
                                  "completed_all": True}},
                     {"platformer": {"unlocked": 59,
                                     "completed_all": True}}):
        sokoban.select_level(FakeWin(mash), {}, progress)
        platformer.select_level(FakeWin(mash), {}, progress)
    # locked endless cannot be chosen without completing everything
    assert platformer.select_level(
        FakeWin([ord("e")]), {}, {}) is None
    assert sokoban.select_level(
        FakeWin([10]), {}, {}) == ("level", 0)


def test_round29_game_over_returns_on_any_key():
    import curses
    from gamebored import ui as ui_mod

    class FakeWin:
        def __init__(self):
            self.shown = []

        def getmaxyx(self):
            return (24, 80)

        def clear(self):
            pass

        def refresh(self):
            pass

        def timeout(self, delay):
            pass

        def addstr(self, y, x, text, attr=0):
            self.shown.append(text)

        def addch(self, y, x, ch, attr=0):
            self.shown.append(ch)

        def getch(self):
            return ord("z")

    win = FakeWin()
    assert ui_mod.game_over_screen(win, "Snake", [], score=5, best=9,
                                   game_id="snake") == ord("z")
    assert any("any key" in line for line in win.shown
                 if isinstance(line, str))


def test_round24_pong_ignores_bad_step_input():
    from gamebored.games import pong
    st = pong.PongState(width=30, height=10)
    for bad in ("x", None, [1]):
        st.step(bad)  # must not raise
    st.step(999)  # must not raise


def test_round25_breakout_ignores_bad_step_input():
    from gamebored.games import breakout
    st = breakout.BreakState()
    for bad in ("x", None, [1]):
        st.step(bad)  # must not raise
    for _ in range(200):
        st.step(1)
    assert st.score >= 0


def test_round26_invaders_level_is_always_sane():
    from gamebored.games import invaders
    for bad in ("x", None, 0, -3):
        st = invaders.InvaderState(width=50, height=18, seed=1, level=bad)
        assert st.level >= 1
        st.score += 10 * st.level
        assert isinstance(st.score, int)
        st.step()


def test_round27_tetris_ignores_bad_moves():
    from gamebored.games import tetris
    st = tetris.TetrisState(seed=0)
    assert st.move("x", None) is False
    st.rotate_piece()  # must not crash
    st.over = True
    assert st.move(0, 1) is False
    st.piece = None
    st.over = False
    st.rotate_piece()  # must not crash
    assert st.move(0, 1) is False
