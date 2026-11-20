"""Simon: watch the flashing sequence, then repeat it.

The machine plays a growing sequence on four pads (keys 1-4). Repeat it
back exactly. Each round you survive adds one step; one mistake ends the
run. Your raw score is rounds cleared.
"""

import curses
import random
import time

from .. import scores as scores_mod
from .. import ui

TITLE = "Simon"
DESCRIPTION = "Repeat the memory sequence"
CONTROLS = "Watch, then press 1-4 | p pause | ? help | q menu"
GAME_ID = "simon"
CATEGORY = "PUZZLE"

PADS = ("1", "2", "3", "4")


class SimonState:
    """Headless memory-sequence logic: no curses calls in here."""

    def __init__(self, seed=None):
        self.rng = random.Random(seed)
        self.seq = [self.rng.randrange(4)]
        self.pos = 0
        self.rounds = 0  # fully repeated rounds (raw score)
        self.over = False

    @property
    def score(self):
        return self.rounds

    def expected(self):
        if self.over or self.pos >= len(self.seq):
            return None
        return self.seq[self.pos]

    def press(self, pad):
        """Press pad 0-3. Returns 'next', 'round', 'gameover', or 'idle'."""
        if self.over:
            return "gameover"
        if pad == self.seq[self.pos]:
            self.pos += 1
            if self.pos >= len(self.seq):
                self.rounds += 1
                self.seq.append(self.rng.randrange(4))
                self.pos = 0
                return "round"
            return "next"
        self.over = True
        return "gameover"


def new_state(seed=None):
    return SimonState(seed)


def draw(screen, st, highlight=None):
    h, w = screen.getmaxyx()
    ui.centered(screen, 1, "SIMON  round:%d  score:%d" % (
        len(st.seq), st.rounds), ui.color(3) | curses.A_BOLD)
    labels = ["[1]", "[2]", "[3]", "[4]"]
    colors = [ui.color(5), ui.color(2), ui.color(4), ui.color(6)]
    total_w = 4 * 6
    x0 = max(0, (w - total_w) // 2)
    y = min(h - 4, 8)
    for i, label in enumerate(labels):
        attr = colors[i]
        if highlight == i:
            attr = curses.A_REVERSE | curses.A_BOLD
        ui.safe_addstr(screen, y, x0 + i * 6, label, attr)
    ui.centered(screen, y + 2, "Watch... then repeat!",
                ui.color(7))


def flash_sequence(screen, st, delay=0.45):
    """Play back the sequence with flashes. Returns False if user quits."""
    try:
        screen.timeout(-1)
    except curses.error:
        pass
    draw(screen, st)
    ui.footer(screen, "Watch the sequence...")
    try:
        screen.refresh()
    except curses.error:
        pass
    time.sleep(0.5)
    for pad in st.seq:
        try:
            screen.clear()
        except curses.error:
            pass
        draw(screen, st, highlight=pad)
        try:
            screen.refresh()
        except curses.error:
            pass
        time.sleep(delay)
        try:
            screen.clear()
        except curses.error:
            pass
        draw(screen, st)
        try:
            screen.refresh()
        except curses.error:
            pass
        time.sleep(0.15)
    try:
        screen.timeout(0)
        key = screen.getch()
        screen.timeout(-1)
        if key in ui.QUIT_KEYS:
            return False
        if key != -1:
            try:
                curses.ungetch(key)
            except curses.error:
                pass
    except curses.error:
        pass
    return True


def play(stdscr, score_store):
    curses.curs_set(0)
    try:
        stdscr.keypad(True)
        stdscr.timeout(-1)
    except curses.error:
        pass
    st = SimonState()
    while True:
        if ui.too_small(stdscr):
            ui.show_too_small(stdscr)
            try:
                key = stdscr.getch()
            except curses.error:
                key = -1
            if key in ui.QUIT_KEYS:
                return
            continue
        if not flash_sequence(stdscr, st,
                              delay=max(0.22, 0.45 - len(st.seq) * 0.015)):
            scores_mod.record_play(score_store, GAME_ID, st.score)
            scores_mod.save(score_store)
            return
        # input phase
        done_round = False
        while not done_round and not st.over:
            try:
                stdscr.clear()
            except curses.error:
                pass
            draw(stdscr, st)
            ui.footer(stdscr, "Your turn: press 1-4 (%d of %d) | q quit" %
                      (st.pos + 1, len(st.seq)))
            try:
                stdscr.refresh()
            except curses.error:
                pass
            try:
                key = stdscr.getch()
            except curses.error:
                key = -1
            if key in ui.QUIT_KEYS:
                scores_mod.record_play(score_store, GAME_ID, st.score)
                scores_mod.save(score_store)
                return
            if key in ui.PAUSE_KEYS:
                if ui.pause_overlay(stdscr) == "quit":
                    return
                continue
            if key in ui.HELP_KEYS:
                ui.show_help_overlay(stdscr, TITLE, CONTROLS)
                continue
            if key == curses.KEY_RESIZE:
                continue
            if ord("1") <= key <= ord("4"):
                result = st.press(key - ord("1"))
                if result == "round":
                    done_round = True
                elif result == "gameover":
                    break
        if st.over:
            entry = scores_mod.get_entry(score_store, GAME_ID)
            _, is_high = scores_mod.record_play(score_store, GAME_ID,
                                                st.score, won=False)
            scores_mod.save(score_store)
            ui.game_over_screen(
                stdscr, TITLE,
                ["Wrong pad! You cleared %d round%s." % (
                    st.rounds, "" if st.rounds == 1 else "s")],
                score=st.score, best=max(entry["high"], st.score),
                is_new_high=is_high, game_id=GAME_ID, won=False)
            return
