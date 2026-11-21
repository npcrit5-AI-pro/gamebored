"""Headless PTY tests: launch every game from the real menu, play, quit cleanly.

Uses pexpect (test-only dependency) to drive the actual curses UI in a
pseudo-terminal at 80x24, proving the menu launches each game, accepts
input, and returns to the menu / exits without breaking the terminal.
"""

import os
import re
import sys
import time

import pytest

pexpect = pytest.importorskip("pexpect")

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV = dict(os.environ, TERM="xterm-256color",
           PYTHONPATH=REPO + os.pathsep + os.environ.get("PYTHONPATH", ""))
# Curses honors LINES/COLUMNS over the real pty size: never inherit them.
ENV.pop("LINES", None)
ENV.pop("COLUMNS", None)
ENV["HOME"] = os.environ.get("HOME", "/root")  # scores go to real home; harmless

MENU_RE = re.compile(r"Pick a game", re.S)
TOO_SMALL_RE = re.compile(r"Make the window bigger", re.S)


def spawn(w=80, h=24):
    child = pexpect.spawn(
        sys.executable, ["-m", "gamebored"],
        cwd=REPO, dimensions=(h, w), timeout=15,
        encoding="utf-8", codec_errors="ignore", env=ENV,
    )
    child.delaybeforesend = 0.05
    return child


def expect_menu(child):
    child.expect(MENU_RE)


def quit_to_menu(child):
    """Press q (and Enter as fallback for game-over screens), expect menu."""
    for _ in range(4):
        child.send("q")
        time.sleep(0.4)
        try:
            child.expect(MENU_RE, timeout=3)
            return
        except pexpect.TIMEOUT:
            child.send("\r")
            time.sleep(0.3)
    child.expect(MENU_RE, timeout=5)


def close(child):
    try:
        child.send("q")
        child.expect(pexpect.EOF, timeout=10)
    finally:
        try:
            child.close()
        except Exception:
            pass
    assert child.exitstatus == 0, "app exited with %r" % (child.exitstatus,)


# (menu key, extra gameplay keys to prove input works)
GAME_KEYS = [
    ("1", "\x1b[B\x1b[A"),   # snake: arrows change direction
    ("2", "\x1b[D\x1b[C\x1b[A"),  # tetris: move + rotate
    ("3", "\x1b[A\x1b[B\x1b[D\x1b[C"),  # 2048: slide around
    ("4", "\x1b[B\x1b[C f"),  # minesweeper: move + flag
    ("5", "5"),               # tictactoe: place at 5
    ("6", "aeiou"),           # hangman: guess vowels (q quits, so no q here)
    ("7", "\x1b[A\x1b[B"),    # pong: move paddle
    ("8", "ad "),             # invaders: move + shoot
    ("9", "ad"),              # breakout: move paddle
    ("0", "crate\r"),         # wordle: type a word + submit
    ("a", "\x1b[A\x1b[B\x1b[C\x1b[D"),  # frogger: hop around
    ("b", "1234"),            # simon: repeat-ish input
    ("c", "\r\x1b[A\x1b[B\x1b[C\x1b[D"),  # sokoban: pick room 1, push around
    ("d", "4"),               # connect4: drop in column 4
    ("e", "   "),             # flappy: flap a few times
    ("f", "\r\x1b[C\x1b[C "),  # runner: pick room 1, run + jump
    ("h", ""),                # high scores table
]


@pytest.mark.parametrize("key,inputs", GAME_KEYS)
def test_each_game_launches_accepts_input_and_quits(key, inputs):
    child = spawn()
    try:
        expect_menu(child)
        child.send(key)
        time.sleep(1.5)  # let the game boot and tick
        child.send(inputs)
        time.sleep(1.0)
        quit_to_menu(child)  # back at menu: game exited cleanly
    finally:
        close(child)


def test_menu_navigation_and_quit():
    child = spawn()
    try:
        expect_menu(child)
        child.send("\x1b[B")  # down
        time.sleep(0.3)
        child.send("\x1b[A")  # up
        time.sleep(0.3)
        child.send("\r")  # enter launches snake (selected=0)
        time.sleep(1.5)
        quit_to_menu(child)
    finally:
        close(child)


def test_translator_converts_and_returns():
    child = spawn()
    try:
        expect_menu(child)
        child.send("t")  # open the Score Translator
        time.sleep(1.0)
        child.expect(re.compile(r"SCORE TRANSLATOR", re.S), timeout=5)
        child.send("1")  # pick Snake
        time.sleep(1.0)
        child.expect(re.compile(r"raw score", re.S), timeout=5)
        child.send("100\r")  # raw number + Enter converts
        time.sleep(1.0)
        child.expect(re.compile(r"10,000 BP", re.S), timeout=5)
        child.send("q")  # back to game picker (no Enter: it re-selects)
        time.sleep(0.8)
        child.send("q")  # back to the menu
        expect_menu(child)
    finally:
        close(child)


def test_small_terminal_shows_friendly_message():
    child = spawn(w=40, h=10)
    try:
        child.expect(TOO_SMALL_RE, timeout=10)
        child.send("q")
        child.expect(pexpect.EOF, timeout=10)
    finally:
        try:
            child.close()
        except Exception:
            pass
    assert child.exitstatus == 0


def test_resize_back_to_full_restores_menu():
    child = spawn()
    try:
        expect_menu(child)
        child.setwinsize(10, 40)
        time.sleep(0.5)
        child.send("x")  # not q: message screen stays, no crash
        time.sleep(0.5)
        child.setwinsize(24, 80)
        time.sleep(0.5)
        child.send("x")  # any key retries size check -> menu redraws
        expect_menu(child)
    finally:
        close(child)


MENU_EXTRAS_RE = re.compile(r"Bored Wondering", re.S)
HELP_RE = re.compile(r"GAMEBORED HELP", re.S)
SCORES_RE = re.compile(r"HIGH SCORES", re.S)
TRANSLATOR_RE = re.compile(r"SCORE TRANSLATOR", re.S)
WONDER_RE = re.compile(r"BORED WONDERING", re.S)
PAUSED_RE = re.compile(r"PAUSED", re.S)


def test_menu_shows_grouped_entries_and_footer(tmp_path, monkeypatch):
    # Fresh HOME: no remembered menu selection, so the list starts at top.
    monkeypatch.setitem(ENV, "HOME", str(tmp_path))
    child = spawn()
    try:
        expect_menu(child)
        child.expect(re.compile(r"ACTION", re.S), timeout=5)
        child.expect(re.compile(r"Combined total: .* BP", re.S), timeout=5)
        for _ in range(16):  # scroll down to the EXPLORE group
            child.send("\x1b[B")
            time.sleep(0.15)
        child.expect(re.compile(r"EXPLORE", re.S), timeout=5)
        child.expect(MENU_EXTRAS_RE, timeout=5)
        child.expect(re.compile(r"Score Translator", re.S), timeout=5)
    finally:
        close(child)


def test_hotkeys_open_and_close_extra_screens():
    child = spawn()
    try:
        expect_menu(child)
        for key, pattern in (("H", SCORES_RE), ("T", TRANSLATOR_RE),
                             ("?", HELP_RE)):
            child.send(key)
            time.sleep(1.0)
            child.expect(pattern, timeout=5)
            child.send("q")  # back to menu (help closes on any key)
            time.sleep(0.8)
            expect_menu(child)
    finally:
        close(child)


def test_wondering_search_flow_stays_friendly():
    child = spawn()
    try:
        expect_menu(child)
        child.send("W")
        time.sleep(1.0)
        child.expect(WONDER_RE, timeout=5)
        child.send("penguins")
        time.sleep(0.5)
        child.send("\r")  # search (live APIs or friendly offline message)
        time.sleep(6.0)
        child.expect(re.compile(r"results for|No internet|No results", re.S),
                     timeout=15)
        child.send("\x1b")  # Esc back to menu
        time.sleep(1.0)
        quit_to_menu(child)
    finally:
        close(child)


def test_pause_overlay_resumes_game():
    child = spawn()
    try:
        expect_menu(child)
        child.send("1")  # snake
        time.sleep(1.5)
        child.send("p")
        time.sleep(0.8)
        child.expect(PAUSED_RE, timeout=5)
        child.send("p")  # resume
        time.sleep(0.8)
        quit_to_menu(child)
    finally:
        close(child)


def test_in_game_help_overlay_closes_cleanly():
    child = spawn()
    try:
        expect_menu(child)
        child.send("1")  # snake
        time.sleep(1.5)
        child.send("?")
        time.sleep(0.8)
        child.expect(HELP_RE, timeout=5)
        child.send("x")  # any key closes the overlay
        time.sleep(0.8)
        quit_to_menu(child)
    finally:
        close(child)


def test_level_select_opens_and_starts_sokoban():
    child = spawn()
    try:
        expect_menu(child)
        child.send("c")  # sokoban -> room picker
        time.sleep(1.0)
        child.expect(re.compile(r"PICK A ROOM", re.S), timeout=5)
        child.expect(re.compile(r"room\s+1", re.S), timeout=5)
        child.send("\r")  # start room 1
        time.sleep(1.0)
        child.send("\x1b[C")  # push around
        time.sleep(0.8)
        child.expect(re.compile(r"SOKOBAN", re.S), timeout=5)
        quit_to_menu(child)  # q from gameplay records score, back to menu
    finally:
        close(child)


def test_level_select_opens_and_starts_runner():
    child = spawn()
    try:
        expect_menu(child)
        child.send("f")  # runner -> room picker
        time.sleep(1.0)
        child.expect(re.compile(r"PICK A ROOM", re.S), timeout=5)
        child.expect(re.compile(r"room\s+1", re.S), timeout=5)
        child.send("\r")  # start room 1
        time.sleep(1.0)
        child.send("\x1b[C ")  # run + jump
        time.sleep(1.0)
        child.expect(re.compile(r"RUNNER", re.S), timeout=5)
        quit_to_menu(child)
    finally:
        close(child)
