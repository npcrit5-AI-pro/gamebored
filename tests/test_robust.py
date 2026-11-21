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


def test_round50_high_scores_show_play_counts():
    import curses
    from gamebored import extras as extras_mod

    class FakeWin:
        def __init__(self):
            self.lines = []

        def getmaxyx(self):
            return (24, 80)

        def clear(self):
            pass

        def refresh(self):
            pass

        def addstr(self, y, x, text, attr=0):
            self.lines.append(text)

        def getch(self):
            return ord("q")

    win = FakeWin()
    extras_mod.show_high_scores(
        win, {"snake": {"high": 9, "plays": 2},
              "pong": {"high": 200, "plays": 1}})
    assert any("9 " in ln and "2 plays" in ln for ln in win.lines), win.lines
    assert any("1 play" in ln and "1 plays" not in ln for ln in win.lines)


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


def test_round38_list_shows_sixteen_games_including_runner(capsys):
    from gamebored import __main__ as main_mod
    from gamebored.games import GAMES
    assert main_mod.main(["--list"]) == 0
    out = capsys.readouterr().out
    assert len(GAMES) == 16
    assert "Runner" in out
    for mod in GAMES:
        assert mod.TITLE in out
    from gamebored import translator as translator_mod
    assert translator_mod.rate_for("platformer") > 0


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


def test_round41_sokoban_best_moves_tracked(tmp_path):
    from gamebored import progress as progress_mod
    from gamebored.games import sokoban
    path = str(tmp_path / "progress.json")
    store = {}
    assert progress_mod.get_best(store, "sokoban", 3) is None
    assert progress_mod.record_best(store, "sokoban", 3, 42,
                                    path=path) == 42
    assert progress_mod.record_best(store, "sokoban", 3, 99,
                                    path=path) == 42
    assert progress_mod.record_best(store, "sokoban", 3, 10,
                                    path=path) == 10
    for bad in (0, -5, "x", None):
        assert progress_mod.record_best(store, "sokoban", 3, bad,
                                        path=path) == 10, bad
    assert progress_mod.get_best({"sokoban": "junk"}, "sokoban", 3) is None
    assert progress_mod.get_best({"sokoban": {"best": {"3": "abc"}}},
                                 "sokoban", 3) is None
    # solving a room end to end records its best
    st = sokoban.SokState(level=0)
    assert st.move(0, -1) is True and st.over
    store2 = {}
    progress_mod.record_best(store2, "sokoban", 0, st.moves, path=path)
    assert progress_mod.get_best(store2, "sokoban", 0) == st.moves > 0


def test_round42_menu_remembers_last_pick(tmp_path):
    from gamebored import app as app_mod
    entries = app_mod.build_entries()
    assert app_mod._restore_selected({}, entries) == 0
    assert app_mod._restore_selected({"_menu_last": "nope"}, entries) == 0
    assert app_mod._restore_selected(None, entries) == 0
    assert app_mod._restore_selected({"_menu_last": 5}, entries) == 0
    store = {}
    target = next(i for i, e in enumerate(entries)
                  if e.get("kind") == "game"
                  and e["mod"].GAME_ID == "platformer")
    app_mod._remember_selected(store, entries, target)
    assert store["_menu_last"] == "game:platformer"
    assert app_mod._restore_selected(store, entries) == target
    # corrupt store shapes never raise, saves still work
    app_mod._remember_selected([], entries, target)
    app_mod._remember_selected(store, [], target)
    path = str(tmp_path / "scores.json")
    from gamebored import scores as scores_mod
    scores_mod.save(store, path)
    reloaded = scores_mod.load(path)
    assert app_mod._restore_selected(reloaded, entries) == target


def test_round43_menu_filter_narrows_and_opens():
    import curses
    from gamebored import app as app_mod
    entries = app_mod.build_entries()
    assert app_mod._apply_filter(entries, "") == entries
    assert app_mod._apply_filter(entries, "   ") == entries
    hits = app_mod._apply_filter(entries, "sok")
    assert hits and all("sok" in (e["title"] + e["desc"]).lower()
                        for e in hits)
    assert app_mod._apply_filter(entries, "zzz-no-such-game") == []
    assert app_mod._apply_filter(entries, "F")  # hotkey match
    assert app_mod._apply_filter(None, "x") == []

    class FakeWin:
        def __init__(self, keys):
            self.keys = list(keys)
            self.status_seen = []

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
            if isinstance(text, str) and text.startswith("Filter:"):
                self.status_seen.append(text)

        def addch(self, y, x, ch, attr=0):
            pass

        def getch(self):
            return self.keys.pop(0) if self.keys else ord("q")

    # type a filter, back it out, quit: never launches anything
    win = FakeWin([ord("/"), ord("s"), ord("o"), ord("k"),
                   curses.KEY_BACKSPACE, 27, ord("q")])
    app_mod.menu_loop(win)
    assert any("sok" in s.lower() for s in win.status_seen)
    # filter with no matches shows the empty message, Esc exits
    win2 = FakeWin([ord("/"), ord("z"), ord("z"), ord("z"), 27, ord("q")])
    app_mod.menu_loop(win2)
    assert any("(0 match" in s for s in win2.status_seen)


def test_round44_runner_restart_room_keeps_score_and_lives():
    from gamebored.games import platformer
    st = platformer.RunState(platformer.LEVELS[0], score=250)
    st.lives = 2
    st.step(0.09, move=1)
    keep_score, keep_lives = st.score, st.lives
    fresh = platformer.RunState(st.lv["rows"], score=keep_score,
                               endless=st.endless)
    fresh.lives = keep_lives
    assert fresh.score == keep_score and fresh.lives == keep_lives
    assert (fresh.x, fresh.y) == (float(st.lv["spawn"][0]),
                                  float(st.lv["spawn"][1]))
    assert "r restart room" in platformer.CONTROLS


def test_round45_every_game_advertises_pause_help_menu():
    from gamebored.games import GAMES
    assert len(GAMES) == 16
    for mod in GAMES:
        controls = mod.CONTROLS.lower()
        assert "p" in controls and "pause" in controls, mod.GAME_ID
        assert "?" in controls and "help" in controls, mod.GAME_ID
        assert "q" in controls and "menu" in controls, mod.GAME_ID


def test_round52_wondering_names_both_quit_keys():
    from gamebored import ui as ui_mod
    from gamebored import wondering as wondering_mod
    assert not hasattr(ui_mod, "FOOTER_HELP")  # dead shortcut text removed
    assert "q" in wondering_mod.CONTROLS and "menu" in wondering_mod.CONTROLS


def test_round53_pause_names_the_game():
    from gamebored import ui as ui_mod

    class FakeWin:
        def __init__(self, keys):
            self.keys = list(keys)
            self.lines = []

        def getmaxyx(self):
            return (24, 80)

        def refresh(self):
            pass

        def timeout(self, delay):
            pass

        def addstr(self, y, x, text, attr=0):
            self.lines.append(text)

        def addch(self, y, x, ch, attr=0):
            self.lines.append(ch)

        def getch(self):
            return self.keys.pop(0) if self.keys else ord("p")

    win = FakeWin([ord("p")])
    assert ui_mod.pause_overlay(win, "Snake") == "resume"
    assert any("PAUSED - Snake" in ln for ln in win.lines
               if isinstance(ln, str)), win.lines
    win2 = FakeWin([ord("q")])
    assert ui_mod.pause_overlay(win2) == "quit"


def test_round46_picker_shows_best_moves():
    from gamebored.games import sokoban

    class FakeWin:
        def __init__(self):
            self.lines = []

        def getmaxyx(self):
            return (24, 80)

        def clear(self):
            pass

        def refresh(self):
            pass

        def addstr(self, y, x, text, attr=0):
            self.lines.append(text)

        def getch(self):
            return 10

    progress = {"sokoban": {"unlocked": 5,
                            "best": {"0": 7, "2": 31}}}
    assert sokoban.select_level(FakeWin(), {}, progress) == ("level", 5)
    win = FakeWin()
    sokoban.select_level(win, {}, progress)
    assert any("room   1 (best 7)" in ln for ln in win.lines), win.lines
    assert any("room   3 (best 31)" in ln for ln in win.lines)
    assert any("[locked]" in ln for ln in win.lines)


def test_round47_runner_death_costs_one_life_and_warns():
    from gamebored.games import platformer
    st = platformer.RunState(platformer.LEVELS[0], score=100)
    assert st.lives == platformer.LIVES
    assert st._die() == "dead"
    assert st.lives == platformer.LIVES - 1 and not st.over
    assert (st.x, st.y) == (float(st.lv["spawn"][0]),
                            float(st.lv["spawn"][1]))
    st.lives = 1
    assert st._die() == "dead-over"
    assert st.over and not st.won


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


def test_round40_sokoban_undo_takes_back_moves():
    from gamebored.games import sokoban
    st = sokoban.SokState(level=0)
    assert st.undo() is False  # nothing to undo
    p0, boxes0 = st.player, set(st.boxes)
    assert st.move(0, -1) is True  # shove the box up onto its target
    assert st.undo() is True
    assert st.player == p0 and st.boxes == boxes0 and st.moves == 0
    assert st.undo() is False
    # pushing a box then undoing restores the box too
    st2 = sokoban.SokState(level=1)
    assert st2.move(-1, 0) is True
    assert st2.move(1, 0) is True
    mid_player, mid_boxes = st2.player, set(st2.boxes)
    assert st2.move(-1, 0) is True
    assert st2.undo() is True
    assert st2.player == mid_player and st2.boxes == mid_boxes
    # restart clears the undo trail
    st2.restart()
    assert st2.undo() is False
    # undo caps memory on long sessions
    st3 = sokoban.SokState(level=0, rows=sokoban.LEVELS[1])
    for _ in range(2100):
        st3.move(1, 0)
        st3.move(-1, 0)
    assert len(st3.history) <= 2000


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


def test_round54_pickers_answer_help_key(monkeypatch):
    """Round 54: '?' in Sokoban/Runner room pickers opens help, then q quits."""
    import curses as _c
    from gamebored import ui as ui_mod
    from gamebored.games import sokoban as sk
    from gamebored.games import platformer as pf
    from gamebored import progress as _pg
    import gamebored.scores as _ss

    shown = []
    monkeypatch.setattr(ui_mod, "show_help_overlay",
                        lambda stdscr, gid: shown.append(gid))

    class PickerWin:
        def __init__(self, keys):
            self.keys = list(keys)
            self.lines = []

        def getmaxyx(self):
            return (24, 80)

        def clear(self):
            pass

        def refresh(self):
            pass

        def timeout(self, delay):
            pass

        def keypad(self, flag):
            pass

        def addstr(self, y, x, text, attr=0):
            self.lines.append(text)

        def addch(self, y, x, ch, attr=0):
            self.lines.append(ch)

        def getch(self):
            return self.keys.pop(0) if self.keys else ord("q")

    for mod, gid in ((sk, "sokoban"), (pf, "platformer")):
        win = PickerWin([ord("?"), ord("q")])
        calls = {"n": 0}

        def fake_scores(path=None):
            calls["n"] += 1
            raise AssertionError("picker must not touch real scores")

        try:
            res = mod.select_level(win, _ss, {})
        except AssertionError:
            raise
        assert res is None
    assert sorted(shown) == ["platformer", "sokoban"], shown


def test_round55_sokoban_footer_names_boxes_home():
    """Round 55: footer says 'boxes home N/M', not cryptic 'home N/M'."""
    import inspect
    from gamebored.games import sokoban
    src = inspect.getsource(sokoban.play)
    assert "boxes home %d/%d" in src


def test_round56_runner_controls_say_restart():
    """Round 56: Runner CONTROLS say 'r restart room', not cryptic 'r room'."""
    from gamebored.games import platformer
    assert "restart" in platformer.CONTROLS


def test_round57_picker_footers_advertise_help():
    """Round 57: room-picker footers advertise '? help' (they answer it)."""
    import inspect
    from gamebored.games import sokoban, platformer
    assert "? help" in inspect.getsource(sokoban.select_level)
    assert "? help" in inspect.getsource(platformer.select_level)


def test_round58_help_screen_documents_filter():
    """Round 58: the full Help screen documents '/ filter'."""
    from gamebored import extras
    lines = extras.build_help_lines([])
    assert any("/ filter" in ln or "/ filters" in ln for ln in lines), lines


def test_round59_runner_clear_toast_uses_room_bonus():
    """Round 59: room-clear toast names the real ROOM_BONUS, shows 1.2s."""
    import inspect
    from gamebored.games import platformer
    src = inspect.getsource(platformer.play)
    assert "clear_until = time.time() + 1.2" in src
    assert '" CLEAR! +%d" % ROOM_BONUS' in src


def test_round60_sokoban_solved_toast():
    """Round 60: Sokoban flashes SOLVED! for ~1.2s after clearing a room."""
    import inspect
    from gamebored.games import sokoban
    src = inspect.getsource(sokoban.play)
    assert "solved_until = time.time() + 1.2" in src
    assert src.count("SOLVED!") >= 2  # endless + room labels


def test_round61_runner_footer_score_is_total():
    """Round 61: footer says 'score N' (it persists across rooms)."""
    import inspect
    from gamebored.games import platformer
    src = inspect.getsource(platformer.play)
    assert '" | score %d" % st.score' in src
    assert "room score" not in src
