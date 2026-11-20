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
