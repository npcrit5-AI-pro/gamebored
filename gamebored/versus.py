"""Eliza vs PARRY: watch the two bots talk to each other.

A loving nod to the famous 1972 ARPANET conversation where ELIZA (the
therapist) met PARRY (the paranoid patient). ELIZA opens, then they take
turns with human-feeling think delays. q stops the show. Only stdlib.
"""

import curses

from . import chatui as chatui_mod
from . import cpu as cpu_mod
from . import eliza as eliza_mod
from . import parry as parry_mod
from . import storage as storage_mod
from . import ui

TITLE = "Eliza vs Parry"
DESCRIPTION = "1972 ARPANET rematch, live"
CONTROLS = "q stops the show | PgUp/PgDn scroll"
GAME_ID = "versus"
CATEGORY = "Talk"

SESSION_FILE = "versus_last.txt"
MAX_TURNS = 60

SEED = "Hello. I am worried someone is following me."


def run_exchange(turns=12, seed=None, eliza_path=None):
    """Headless bot-vs-bot transcript: [(who, text)]. No sleeps, no curses.

    ELIZA speaks first (greeting the seed), then PARRY answers ELIZA, and
    they alternate. A throwaway ELIZA session is used unless eliza_path is
    given (tests pass an isolated path so real memory is untouched).
    """
    turns = max(1, min(int(turns or 1), MAX_TURNS))
    estate = eliza_mod.new_session(path=eliza_path)
    pstate = parry_mod.new_state()
    transcript = []
    try:
        current = seed if seed is not None else SEED
        for _ in range(turns):
            answer = eliza_mod.reply(estate, current)
            transcript.append(("ELIZA", answer))
            current = answer
            answer = parry_mod.respond(pstate, current)
            transcript.append(("PARRY", answer))
            current = answer
    except Exception:
        pass
    return transcript


def play(stdscr, _score_store=None):
    try:
        curses.curs_set(0)
    except curses.error:
        pass
    try:
        stdscr.keypad(True)
        stdscr.timeout(-1)
    except curses.error:
        pass
    estate = eliza_mod.new_session()
    pstate = parry_mod.new_state()
    transcript = [("*", "The 1972 ARPANET rematch: ELIZA meets PARRY. "
                        "q stops the show."),
                  ("YOU", SEED)]
    try:
        answer = eliza_mod.reply(estate, SEED)
    except Exception:
        answer = "Please go on."
    transcript.append(("ELIZA", answer))
    current = answer
    scroll = 0
    turn = 1  # ELIZA already opened, so PARRY answers first.
    auto = True
    while True:
        if ui.too_small(stdscr, 14, 50):
            ui.show_too_small(stdscr)
            try:
                key = stdscr.getch()
            except curses.error:
                key = -1
            if key in ui.QUIT_KEYS:
                _save(transcript)
                return
            continue
        scroll = chatui_mod.draw(
            stdscr, "ELIZA vs PARRY  ·  live rematch (turn %d)" % (turn + 1),
            "q stops | PgUp/PgDn scrolls | any other key pauses",
            transcript, scroll, "")
        try:
            stdscr.timeout(150)
            key = stdscr.getch()
        except curses.error:
            key = -1
        finally:
            try:
                stdscr.timeout(-1)
            except curses.error:
                pass
        if key in ui.QUIT_KEYS:
            _save(transcript)
            return
        if key == curses.KEY_PPAGE:
            scroll += 5
            continue
        if key == curses.KEY_NPAGE:
            scroll = max(0, scroll - 5)
            continue
        if key == curses.KEY_RESIZE:
            continue
        if key != -1:
            auto = not auto
            transcript.append(("*", "Paused. Press any key to resume, "
                                    "q to leave."))
            scroll = 0
            try:
                stdscr.timeout(-1)
                key2 = stdscr.getch()
            except curses.error:
                key2 = -1
            if key2 in ui.QUIT_KEYS:
                _save(transcript)
                return
            auto = True
            continue
        if not auto:
            continue
        think = (parry_mod.think_seconds(pstate)
                 if turn % 2 else eliza_mod.think_seconds(estate))
        if cpu_mod.think(stdscr, seconds=think,
                         label="PARRY is thinking" if turn % 2
                         else "ELIZA is thinking") == "quit":
            _save(transcript)
            return
        try:
            if turn % 2:
                current = parry_mod.respond(pstate, current)
                transcript.append(("PARRY", current))
            else:
                current = eliza_mod.reply(estate, current)
                transcript.append(("ELIZA", current))
        except Exception:
            pass
        turn += 1
        scroll = 0
        if turn >= MAX_TURNS:
            transcript.append(("*", "The operators ended the call after "
                                    "%d turns. q leaves." % MAX_TURNS))
            _save(transcript)
            try:
                stdscr.timeout(-1)
                stdscr.getch()
            except curses.error:
                pass
            return


def _save(transcript):
    try:
        path = storage_mod.data_path(SESSION_FILE)
        with open(path + ".tmp", "w", encoding="utf-8") as fh:
            for who, text in transcript or []:
                fh.write("%s: %s\n" % (who or "?", text))
        import os
        os.replace(path + ".tmp", path)
    except OSError:
        pass
