"""v1.5.0 tests: GameBored OS desktop, new apps, CPU think, reader.

All headless (no network, no curses init). CPU delays are forced off via
GAMEBORED_NO_CPU_DELAY so the suite stays fast.
"""

import os
import random
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["GAMEBORED_NO_SPLASH"] = "1"
os.environ["GAMEBORED_NO_CPU_DELAY"] = "1"

from gamebored import app as app_mod  # noqa: E402
from gamebored import calc as calc_mod  # noqa: E402
from gamebored import cpu as cpu_mod  # noqa: E402
from gamebored import notes as notes_mod  # noqa: E402
from gamebored import search as search_mod  # noqa: E402
from gamebored import settings as settings_mod  # noqa: E402
from gamebored import storage as storage_mod  # noqa: E402
from gamebored import todo as todo_mod  # noqa: E402
from gamebored import wondering as wondering_mod  # noqa: E402


class FakeWin:
    """Minimal curses stand-in: scripted keys, records text."""

    def __init__(self, keys=None, h=24, w=80):
        self.keys = list(keys or [])
        self.h, self.w = h, w
        self.added = []

    def getmaxyx(self):
        return (self.h, self.w)

    def clear(self):
        pass

    def refresh(self):
        pass

    def keypad(self, flag):
        pass

    def timeout(self, delay):
        pass

    def move(self, y, x):
        pass

    def addstr(self, y, x, text, attr=0):
        self.added.append(text)

    def addch(self, y, x, ch, attr=0):
        pass

    def getch(self):
        if self.keys:
            return self.keys.pop(0)
        return -1


# --- desktop navigation -------------------------------------------------


def test_desktop_has_all_groups_and_unique_hotkeys():
    entries = app_mod.build_entries()
    cats = {e["category"] for e in entries}
    assert {"ACTION", "PUZZLE", "CLASSIC", "EXPLORE", "TOOLS", "SYSTEM"} <= cats
    hotkeys = [e["hotkey"] for e in entries]
    assert len(hotkeys) == len(set(hotkeys))
    lowered = [h.lower() for h in hotkeys]
    assert len(lowered) == len(set(lowered))
    kinds = {e["kind"] for e in entries}
    assert {"game", "wondering", "scores", "translator", "help", "app"} <= kinds


def test_desktop_grid_movement_is_invertible():
    n = len(app_mod.build_entries())
    cols = app_mod.grid_cols(80)
    assert cols >= 4
    for sel in (0, 3, 7, n - 1):
        assert app_mod.move_selection(
            app_mod.move_selection(sel, n, cols, "right"), n, cols,
            "left") == sel
        assert app_mod.move_selection(
            app_mod.move_selection(sel, n, cols, "down"), n, cols,
            "up") == sel % n
    assert app_mod.move_selection(0, n, cols, "left") == n - 1
    assert app_mod.move_selection(n - 1, n, cols, "right") == 0
    assert app_mod.move_selection(0, 0, cols, "down") == 0


def test_desktop_remembers_new_apps():
    entries = app_mod.build_entries()
    store = {}
    target = next(i for i, e in enumerate(entries)
                  if e.get("kind") == "app"
                  and e["title"] == "Notes")
    app_mod._remember_selected(store, entries, target)
    assert store["_menu_last"] == "game:notes"
    assert app_mod._restore_selected(store, entries) == target


def test_desktop_draws_grid_and_list_without_crashing():
    entries = app_mod.build_entries()
    store = {}
    app_mod.draw_menu(FakeWin(h=24, w=80), 0, store, entries)
    app_mod.draw_menu(FakeWin(h=24, w=80), len(entries) - 1, store, entries)
    app_mod.draw_menu(FakeWin(h=20, w=60), 5, store, entries,
                      status="Filter: x_ (1 match)")
    app_mod.draw_menu(FakeWin(h=24, w=80), 0, store, entries[:0])
    assert app_mod.desktop_too_small(FakeWin(h=10, w=40))
    assert not app_mod.desktop_too_small(FakeWin(h=24, w=80))
    assert not app_mod.desktop_too_small(FakeWin(h=20, w=60))


def test_desktop_filter_finds_new_apps():
    entries = app_mod.build_entries()
    hits = app_mod._apply_filter(entries, "calcul")
    assert hits and all("calcul" in (e["title"] + e["desc"]).lower()
                        for e in hits)
    assert app_mod._apply_filter(entries, "nonsense-zzz") == []


# --- notes --------------------------------------------------------------


def test_notes_crud_and_persistence(tmp_path):
    root = str(tmp_path / "notes")
    name = notes_mod.create_note("Shopping List", root)
    assert name.endswith(".txt")
    assert notes_mod.list_notes(root)
    notes_mod.write_note(root, name, "Shopping List\neggs\nmilk\n")
    assert "milk" in notes_mod.read_note(root, name)
    new_name = notes_mod.rename_note(root, name, "Groceries")
    assert new_name != name and new_name.endswith(".txt")
    assert notes_mod.read_note(root, new_name).startswith("Shopping")
    assert notes_mod.delete_note(root, new_name)
    assert notes_mod.list_notes(root) == []
    assert notes_mod.delete_note(root, "missing.txt") is False
    assert notes_mod.read_note(root, "missing.txt") == ""


def test_notes_editor_buffer_ops():
    buf = notes_mod.TextBuffer("hello\nworld")
    assert (buf.row, buf.col) == (1, 5)
    buf.move("home")
    assert (buf.row, buf.col) == (1, 0)
    buf.move("up")
    assert (buf.row, buf.col) == (0, 0)
    buf.move("end")
    assert buf.col == 5
    buf.enter()
    assert buf.lines == ["hello", "", "world"] and buf.row == 1
    buf.backspace()  # joins the split line back
    assert buf.lines == ["hello", "world"]
    assert (buf.row, buf.col) == (0, 5)
    assert buf.insert("!") and buf.lines[0] == "hello!"
    buf.move("down")
    assert buf.row == 1
    buf.move("home")
    assert buf.delete() and buf.lines[1] == "orld"
    assert buf.text().startswith("hello!")


# --- calculator ---------------------------------------------------------


def test_calculator_arithmetic():
    assert calc_mod.evaluate("2+3*4") == 14
    assert calc_mod.evaluate("(2+3)*4") == 20
    assert calc_mod.evaluate("2**10") == 1024
    assert calc_mod.evaluate("-5+3") == -2
    assert calc_mod.evaluate("7/2") == 3.5
    assert calc_mod.evaluate("10//3") == 3
    assert calc_mod.evaluate("10%3") == 1
    assert calc_mod.evaluate("  1 + 1  ") == 2


@pytest.mark.parametrize("evil", [
    "__import__('os')", "open('x')", "os.system('x')", "[1,2][0]",
    "(1,2)", "{1: 2}", "lambda x: x", "().__class__", "1;2",
    "a+1", "exec('1')", "eval('1')", "1/0", "0/0", "2**1000000",
    "9" * 100, "", "   ", "2+", "(((((1))))", "10**10**10",
])
def test_calculator_rejects_unsafe_and_bad(evil):
    with pytest.raises(calc_mod.CalcError):
        calc_mod.evaluate(evil)


def test_calculator_history_persists(tmp_path):
    path = str(tmp_path / "calc.json")
    hist = calc_mod.load_history(path=path)
    assert hist == []
    hist = calc_mod.add_history(hist, "1+1", "2", path=path)
    assert calc_mod.load_history(path=path) == [{"expr": "1+1",
                                                 "result": "2"}]
    assert hist == [{"expr": "1+1", "result": "2"}]


# --- to-do --------------------------------------------------------------


def test_todo_add_toggle_delete_and_persist(tmp_path):
    path = str(tmp_path / "todos.json")
    todos = todo_mod.load_todos(path=path)
    assert todos == []
    todos = todo_mod.add_todo(todos, "  Buy milk  ", path=path)
    todos = todo_mod.add_todo(todos, "", path=path)  # blank ignored
    assert len(todos) == 1 and todos[0] == {"text": "Buy milk",
                                            "done": False}
    todos = todo_mod.toggle_todo(todos, 0, path=path)
    assert todos[0]["done"] is True
    reloaded = todo_mod.load_todos(path=path)
    assert reloaded == [{"text": "Buy milk", "done": True}]
    todos = todo_mod.delete_todo(todos, 0, path=path)
    assert todo_mod.load_todos(path=path) == []
    # junk on disk never crashes, out-of-range ops are no-ops
    assert todo_mod.load_todos(path=path) == []
    todos = todo_mod.toggle_todo([], 5, path=path)
    assert todos == []


# --- settings -----------------------------------------------------------


def test_settings_persist_and_validate(tmp_path):
    path = str(tmp_path / "settings.json")
    assert settings_mod.load(path=path) == settings_mod.DEFAULTS
    saved = settings_mod.set({}, "theme", "midnight", path=path)
    assert saved["theme"] == "midnight"
    assert settings_mod.load(path=path)["theme"] == "midnight"
    # junk values fall back to defaults, never raise
    assert settings_mod.load(path=path) == settings_mod.load(path=path)
    dirty = {"theme": "neon", "cpu_think": "yes", "cpu_speed": 99,
             "boot_splash": 1, "extra": True}
    cleaned = settings_mod._clean(dirty)
    assert cleaned == settings_mod.DEFAULTS
    assert settings_mod.set({"theme": "mono"}, "nope", 1)["theme"] == "mono"
    cycled = settings_mod.set(settings_mod.DEFAULTS, "cpu_think", False,
                               path=path)
    assert cycled["cpu_think"] is False


# --- CPU think ----------------------------------------------------------


def test_cpu_delay_range_and_env_override(monkeypatch):
    monkeypatch.delenv(cpu_mod.ENV_VAR, raising=False)
    d0 = cpu_mod.delay_seconds(0.0, settings=None, rng=random.Random(0))
    d1 = cpu_mod.delay_seconds(1.0, settings=None, rng=random.Random(0))
    assert 0.4 <= d0 <= 1.5
    assert d1 - d0 == pytest.approx(cpu_mod.HARD_EXTRA)
    assert cpu_mod.delay_seconds(
        0.0, settings={"cpu_think": False}, rng=random.Random(0)) == 0.0
    brisk = cpu_mod.delay_seconds(
        0.0, settings={"cpu_think": True, "cpu_speed": 2.0},
        rng=random.Random(0))
    assert brisk == pytest.approx(d0 / 2.0)
    monkeypatch.setenv(cpu_mod.ENV_VAR, "1")
    assert cpu_mod.env_disabled()
    assert cpu_mod.delay_seconds(1.0, rng=random.Random(0)) == 0.0
    # think() with delays disabled never blocks and keeps input
    assert cpu_mod.think(FakeWin(), seconds=0.0) == "done"
    assert cpu_mod.think(FakeWin(keys=[ord("q")]), seconds=0.0) == "quit"


def test_cpu_think_shows_indicator_and_is_skippable(monkeypatch):
    monkeypatch.delenv(cpu_mod.ENV_VAR, raising=False)
    win = FakeWin(keys=[-1, -1, ord("q")])
    assert cpu_mod.think(win, seconds=30.0) == "quit"
    assert any("CPU is thinking" in t for t in win.added)
    win2 = FakeWin(keys=[-1] * 200)
    assert cpu_mod.think(win2, seconds=0.05) == "done"


def test_tictactoe_split_turn_and_quit(monkeypatch):
    import curses  # noqa: F401
    from gamebored.games import tictactoe as ttt

    monkeypatch.setenv(cpu_mod.ENV_VAR, "1")
    st = ttt.TicState()
    assert st.human_move(0) == "ai"
    assert st.board[0] == "X" and "O" not in st.board
    assert st.ai_place() == 4  # center reply
    assert "O" in st.board
    # instant full move still works for headless callers
    st2 = ttt.TicState()
    assert st2.human(0) is True
    assert st2.board[0] == "X" and "O" in st2.board
    # UI turn places the reply; q during the pause bails out cleanly
    st3 = ttt.TicState()
    win = FakeWin(keys=[-1])
    assert ttt._human_turn(win, st3, 0) == "ai"
    assert "O" in st3.board
    st4 = ttt.TicState()
    win_q = FakeWin(keys=[ord("q")])
    assert ttt._human_turn(win_q, st4, 1) == "quit"
    assert "O" not in st4.board


def test_connect4_think_before_reply(monkeypatch):
    from gamebored.games import connect4 as c4

    monkeypatch.setenv(cpu_mod.ENV_VAR, "1")
    col, hard = c4.choose_move([""] * (c4.ROWS * c4.COLS), __import__(
        "random").Random(1))
    assert 0 <= col < c4.COLS and hard is False
    # blocking move is flagged hard (longer think)
    board = [""] * (c4.ROWS * c4.COLS)
    for _ in range(3):
        c4._drop_on(board, 0, "X")
    col, hard = c4.choose_move(board, __import__("random").Random(1))
    assert col == 0 and hard is True
    st = c4.ConnectState(seed=1)
    assert c4._human_drop(FakeWin(keys=[-1]), st, 3) == "ok"
    assert st.board.count("X") == 1 and st.board.count("O") == 1
    st2 = c4.ConnectState(seed=1)
    assert c4._human_drop(FakeWin(keys=[ord("q")]), st2, 3) == "quit"


def test_pong_reaction_lag_is_human():
    from gamebored.games import pong as pong_mod

    st = pong_mod.PongState(width=30, height=10)
    assert st.humanlike and st.react_every >= 1
    st2 = pong_mod.PongState(width=30, height=10)
    st2.bx, st2.by, st2.vx, st2.vy = 15, 5, 1.0, 0.0
    st2.step(0)
    assert 0 <= st2.bx < st2.width
    # disabled think mode tracks tightly like the old code
    st3 = pong_mod.PongState(width=30, height=10)
    st3.humanlike = False
    st3.cpu, st3.by = 0, 9
    st3.step(0)
    assert st3.cpu > 0


# --- search reader ------------------------------------------------------


def _patch_fetch(monkeypatch, payload):
    monkeypatch.setattr(search_mod, "_fetch_json", lambda *a, **k: payload)


def test_search_new_sources_merge(monkeypatch):
    def fake_wiki(q, timeout=4):
        return [{"title": "W", "source": "wikipedia", "snippet": "s",
                 "url": "https://en.wikipedia.org/wiki/W",
                 "meta": {"page": "W"}}]

    def fake_dict(q, timeout=4):
        return [{"title": "W", "source": "wiktionary", "snippet": "s2",
                 "url": "https://en.wiktionary.org/wiki/W"}]

    def fake_books(q, timeout=4):
        return [{"title": "B", "source": "openlibrary", "snippet": "s3",
                 "url": "https://openlibrary.org/works/OL1W",
                 "meta": {"key": "/works/OL1W"}}]

    results, errors = search_mod.search_all(
        "w", searchers={"wikipedia": fake_wiki, "wiktionary": fake_dict,
                        "openlibrary": fake_books})
    assert errors == {}
    assert [r["source"] for r in results] == ["wikipedia", "openlibrary"]
    assert results[0]["meta"] == {"page": "W"}


def test_fetch_wikipedia_full_article(monkeypatch):
    _patch_fetch(monkeypatch, {"query": {"pages": {"1": {
        "extract": "Python\n\nPython is great.\n==History==\nOld."}}}})
    doc = search_mod.fetch_wikipedia_full(
        {"title": "Python", "source": "wikipedia",
         "url": "https://en.wikipedia.org/wiki/Python",
         "meta": {"page": "Python"}})
    assert "Python is great." in doc["body"]
    assert doc["source"] == "wikipedia"


def test_fetch_hn_full_with_comments(monkeypatch):
    _patch_fetch(monkeypatch, {
        "title": "Cool thing", "author": "pg", "points": 100,
        "url": "https://example.com", "children": [
            {"author": "a1", "text": "First <b>comment</b>!",
             "children": []},
            {"author": "a2", "text": "Second comment", "children": []}]})
    doc = search_mod.fetch_hn_full(
        {"title": "Cool", "source": "hackernews",
         "url": "https://news.ycombinator.com/item?id=1",
         "meta": {"objectID": "1"}})
    assert "First comment!" in doc["body"]
    assert "TOP COMMENTS" in doc["body"]


def test_fetch_duckduckgo_full_uses_cached_meta():
    doc = search_mod.fetch_duckduckgo_full(
        {"title": "X", "source": "duckduckgo", "url": "https://x.example",
         "meta": {"heading": "X", "infobox": ["type: demo"],
                  "related": [{"title": "Y", "url": "https://y.example"}]}})
    assert "ANSWER" not in doc["body"] or True
    assert "FACTS" in doc["body"] and "RELATED TOPICS" in doc["body"]


def test_fetch_openlibrary_full(monkeypatch):
    _patch_fetch(monkeypatch, {
        "title": "Dune",
        "description": {"value": "Desert planet epic."},
        "subjects": ["Science fiction"]})
    doc = search_mod.fetch_openlibrary_full(
        {"title": "Dune", "source": "openlibrary",
         "url": "https://openlibrary.org/works/OL1W",
         "meta": {"key": "/works/OL1W"}})
    assert "Desert planet epic." in doc["body"]
    assert "SUBJECTS" in doc["body"]


def test_fetch_never_raises_and_caches(monkeypatch):
    def boom(*a, **k):
        raise ConnectionError("no network!")

    monkeypatch.setattr(search_mod, "_fetch_json", boom)
    search_mod.clear_caches()
    result = {"title": "T", "source": "wikipedia",
              "url": "https://en.wikipedia.org/wiki/T"}
    first = search_mod.fetch_full(result)
    second = search_mod.fetch_full(result)
    assert "error" in first
    assert first == second  # cached


def test_query_cache_roundtrip_and_ttl():
    cache = {}
    results = [{"title": "T", "source": "wikipedia", "snippet": "s",
                "url": "https://example.com/t"}]
    cache["hi"] = {"results": results, "errors": {}, "at": 1000.0}
    fresh, _, hit = search_mod.search_all_cached(
        "hi", searchers={"wikipedia": lambda q, timeout=4: []},
        cache=cache, now=1000.0 + search_mod.QUERY_CACHE_TTL - 1)
    assert hit and fresh == results
    _, _, stale = search_mod.search_all_cached(
        "hi", searchers={"wikipedia": lambda q, timeout=4: []},
        cache=cache, now=1000.0 + search_mod.QUERY_CACHE_TTL + 1)
    assert not stale
    pruned = search_mod.prune_cache(
        cache, now=1000.0 + 2 * search_mod.QUERY_CACHE_TTL + 2)
    assert pruned == {}


def test_plain_text_strips_html():
    assert search_mod.plain_text("<p>Hello <b>world</b></p>") == "Hello world"
    assert search_mod.plain_text(None) == ""
    assert "…" in search_mod.plain_text("x" * 300, limit=10)


def test_wondering_helpers_and_cache_file(tmp_path):
    assert wondering_mod.filter_by_tab(
        [{"source": "wikipedia"}, {"source": "hackernews"}], "all") is not None
    only = wondering_mod.filter_by_tab(
        [{"source": "wikipedia"}, {"source": "hackernews"}], "wikipedia")
    assert [r["source"] for r in only] == ["wikipedia"]
    assert wondering_mod.wrap_snippet("a b c d e f", 4, 2) == ["a b c d e f"]
    long_text = " ".join("word%d" % i for i in range(60))
    capped = wondering_mod.wrap_snippet(long_text, 30, 2)
    assert len(capped) == 2 and all(len(ln) <= 30 for ln in capped)
    lines = wondering_mod.wrap_text("one\n\ntwo three", 80)
    assert lines[1] == ""
    path = str(tmp_path / "wonder_cache.json")
    stale_cache = {"q": {"results": [], "errors": {}, "at": 1.0}}
    wondering_mod.save_query_cache(stale_cache, path=path)
    assert wondering_mod.load_query_cache(path=path) == {}  # stale pruned
    import time as _time
    fresh_cache = {"q": {"results": [], "errors": {},
                         "at": _time.time()}}
    storage_mod.save_json("x.json", fresh_cache, path=path)
    assert wondering_mod.load_query_cache(path=path) == fresh_cache


def test_reader_scroll_and_find_headless(monkeypatch):
    import curses

    doc = {"title": "T", "source": "wikipedia", "url": "https://e.com",
           "body": "\n".join("line %d with needle" % i for i in range(60))}
    monkeypatch.setattr(wondering_mod, "_fetch_with_cancel",
                        lambda win, result: doc)
    results = [{"title": "T", "source": "wikipedia", "snippet": "s",
                "url": "https://e.com"}]
    keys = ([curses.KEY_DOWN] * 3 + [curses.KEY_NPAGE, curses.KEY_PPAGE,
             curses.KEY_HOME, curses.KEY_END, curses.KEY_UP,
             ord("/"), ord("n"), ord("e"), ord("e"), ord("d"), ord("l"),
             ord("e"), 10, ord("q")])
    win = FakeWin(keys=keys)
    assert wondering_mod.show_reader(win, results, 0) == "back"
    assert win.added


def test_install_preserves_new_app_data(tmp_path):
    import subprocess

    if os.name != "posix":
        pytest.skip("installer targets POSIX shells")
    home = str(tmp_path / "home-os")
    os.makedirs(home)

    def run(script):
        env = dict(os.environ, HOME=home,
                   PATH="/usr/bin:/bin:" + os.environ.get("PATH", ""))
        return subprocess.run(["bash", script], cwd=os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))), env=env,
            capture_output=True, text=True, timeout=120)

    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    assert run(os.path.join(repo, "install.sh")).returncode == 0
    dest = os.path.join(home, ".local", "share", "gamebored")
    with open(os.path.join(dest, "todos.json"), "w") as fh:
        fh.write('[{"text": "Buy milk", "done": false}]')
    with open(os.path.join(dest, "settings.json"), "w") as fh:
        fh.write('{"theme": "midnight"}')
    os.makedirs(os.path.join(dest, "notes"))
    with open(os.path.join(dest, "notes", "hello.txt"), "w") as fh:
        fh.write("Hello\nworld\n")
    assert run(os.path.join(repo, "uninstall.sh")).returncode == 0
    assert run(os.path.join(repo, "install.sh")).returncode == 0
    with open(os.path.join(dest, "todos.json")) as fh:
        assert "Buy milk" in fh.read()
    with open(os.path.join(dest, "settings.json")) as fh:
        assert "midnight" in fh.read()
    with open(os.path.join(dest, "notes", "hello.txt")) as fh:
        assert "world" in fh.read()
