"""Unit tests for Bored Wondering search (network fully mocked)."""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gamebored import search as search_mod
from gamebored import wondering as wondering_mod


def _r(title, source, snippet, url):
    return {"title": title, "source": source, "snippet": snippet, "url": url}


def test_merge_prefers_wikipedia_and_dedupes_url():
    per = {
        "wikipedia": [_r("Python", "wikipedia", "lang", "https://en.wikipedia.org/wiki/Python")],
        "duckduckgo": [_r("Python", "duckduckgo", "lang", "https://en.wikipedia.org/wiki/Python")],
        "hackernews": [_r("Python talk", "hackernews", "hn", "https://news.ycombinator.com/item?id=1")],
    }
    merged = search_mod.merge_results(per)
    assert len(merged) == 2
    assert merged[0]["source"] == "wikipedia"  # first source wins ties
    assert merged[1]["source"] == "hackernews"


def test_merge_dedupes_title_case_insensitive_and_trailing_slash():
    per = {
        "wikipedia": [],
        "duckduckgo": [_r("Cool Thing", "duckduckgo", "s", "https://example.com/a/")],
        "hackernews": [_r("cool thing", "hackernews", "s2", "https://example.com/a")],
    }
    assert len(search_mod.merge_results(per)) == 1


def test_merge_skips_empty_titles_and_urls():
    per = {
        "wikipedia": [_r("", "wikipedia", "s", "https://example.com/x"),
                      _r("T", "wikipedia", "s", "")],
        "duckduckgo": [_r("Good", "duckduckgo", "s", "https://example.com/g")],
        "hackernews": [],
    }
    merged = search_mod.merge_results(per)
    assert [m["title"] for m in merged] == ["Good"]


def test_search_all_merges_parallel_results():
    calls = []

    def fake_wiki(q, timeout=4):
        calls.append(("wiki", q))
        return [_r("W", "wikipedia", "s", "https://en.wikipedia.org/wiki/W")]

    def fake_ddg(q, timeout=4):
        calls.append(("ddg", q))
        return [_r("D", "duckduckgo", "s", "https://duckduckgo.com/D")]

    def fake_hn(q, timeout=4):
        calls.append(("hn", q))
        return [_r("H", "hackernews", "s", "https://news.ycombinator.com/item?id=9")]

    results, errors = search_mod.search_all(
        "hello", searchers={"duckduckgo": fake_ddg, "wikipedia": fake_wiki,
                            "hackernews": fake_hn})
    assert errors == {}
    assert [r["source"] for r in results] == ["wikipedia", "duckduckgo", "hackernews"]
    assert {c[1] for c in calls} == {"hello"}
    assert len(calls) == 3


def test_search_all_keeps_working_when_one_source_fails():
    def boom(q, timeout=4):
        raise ConnectionError("no network!")

    def ok(q, timeout=4):
        return [_r("Fine", "wikipedia", "s", "https://en.wikipedia.org/wiki/Fine")]

    results, errors = search_mod.search_all(
        "hi", searchers={"duckduckgo": boom, "wikipedia": ok})
    assert [r["title"] for r in results] == ["Fine"]
    assert "duckduckgo" in errors
    assert errors["duckduckgo"]  # friendly, non-empty


def test_search_all_timeout_message_is_friendly():
    import socket

    def slow(q, timeout=4):
        raise socket.timeout("timed out")

    results, errors = search_mod.search_all("hi", searchers={"wikipedia": slow})
    assert results == []
    assert "timed out" in errors["wikipedia"]


def test_search_all_empty_query_calls_nothing():
    def boom(q, timeout=4):
        raise AssertionError("should not be called")

    assert search_mod.search_all("   ", searchers={"wikipedia": boom}) == ([], {})


def test_search_all_never_raises_on_garbage_payloads():
    def junk(q, timeout=4):
        return [{"title": "", "source": "wikipedia", "snippet": "", "url": ""}]

    results, errors = search_mod.search_all("x", searchers={"wikipedia": junk})
    assert results == [] and errors == {}


def test_history_roundtrip_without_touching_disk(monkeypatch):
    store = {}
    monkeypatch.setattr("gamebored.scores.save", lambda *a, **k: None)
    wondering_mod.add_history(store, "  Penguins ")
    wondering_mod.add_history(store, "penguins")  # dup (case-insensitive)
    wondering_mod.add_history(store, "tetris")
    assert wondering_mod.get_history(store) == ["tetris", "penguins"]


def test_only_search_uses_network_imports():
    import pathlib
    root = pathlib.Path(__file__).resolve().parent.parent / "gamebored"
    allowed = {"search.py", "wondering.py"}
    offenders = []
    for path in list(root.glob("*.py")) + list((root / "games").glob("*.py")):
        if path.name in allowed:
            continue
        text = path.read_text()
        for token in ("urllib", "socket", "http.client", "requests"):
            if token in text:
                offenders.append("%s imports %s" % (path.name, token))
    assert offenders == []


def test_live_wikipedia_smoke():
    """Optional live check: skipped when offline (never fails CI)."""
    try:
        results = search_mod.search_wikipedia("python", timeout=8)
    except Exception as exc:
        pytest.skip("offline or Wikipedia unreachable: %s" % exc)
    assert results, "expected at least one live Wikipedia hit"
    assert results[0]["url"].startswith("https://en.wikipedia.org/wiki/")
