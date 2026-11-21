"""Pong vs the computer. First to 5 wins."""

import curses
import time

from .. import scores as scores_mod
from .. import ui

TITLE = "Pong"
DESCRIPTION = "Classic paddle duel vs CPU"
CONTROLS = "Up/Down or W/S move | first to 5 | p pause | ? help | q menu"
GAME_ID = "pong"
CATEGORY = "ACTION"
WIN_SCORE = 5


class PongState:
    def __init__(self, width=60, height=18):
        self.width = width
        self.height = height
        self.player = height // 2
        self.cpu = height // 2
        self.paddle = 4
        self.reset(1)
        self.player_score = 0
        self.cpu_score = 0
        self.over = False
        self.won = False

    def reset(self, direction=1):
        self.bx = self.width // 2
        self.by = self.height // 2
        self.vx = 1.0 * direction
        self.vy = 0.5 if (self.height % 2 == 0) else -0.5

    def step(self, player_move=0, cpu_speed=0.6):
        try:
            player_move = int(player_move)
        except (TypeError, ValueError):
            player_move = 0
        try:
            cpu_speed = float(cpu_speed)
        except (TypeError, ValueError):
            cpu_speed = 0.6
        self.player = max(self.paddle // 2,
                          min(self.height - 1 - self.paddle // 2,
                              self.player + player_move))
        # CPU tracks the ball with limited speed
        if self.cpu < self.by:
            self.cpu = min(self.cpu + cpu_speed, self.height - 1)
        elif self.cpu > self.by:
            self.cpu = max(self.cpu - cpu_speed, 0)
        self.bx += self.vx
        self.by += self.vy
        if self.by <= 0:
            self.by = 0
            self.vy = abs(self.vy)
        elif self.by >= self.height - 1:
            self.by = self.height - 1
            self.vy = -abs(self.vy)
        # paddles at x=1 (player) and x=width-2 (cpu)
        if self.vx < 0 and int(round(self.bx)) <= 2:
            if abs(self.by - self.player) <= self.paddle // 2 + 0.5:
                self.bx = 2
                self.vx = abs(self.vx) * 1.05
                self.vy += (self.by - self.player) * 0.25
        if self.vx > 0 and int(round(self.bx)) >= self.width - 3:
            if abs(self.by - self.cpu) <= self.paddle // 2 + 0.5:
                self.bx = self.width - 3
                self.vx = -abs(self.vx) * 1.05
                self.vy += (self.by - self.cpu) * 0.25
        if self.bx < 0:
            self.cpu_score += 1
            self._check_end()
            if not self.over:
                self.reset(1)
        elif self.bx >= self.width:
            self.player_score += 1
            self._check_end()
            if not self.over:
                self.reset(-1)

    def _check_end(self):
        if self.player_score >= WIN_SCORE:
            self.over = True
            self.won = True
        elif self.cpu_score >= WIN_SCORE:
            self.over = True
            self.won = False


def draw(screen, st, ox, oy):
    for y in range(st.height):
        for x in range(st.width):
            ch = " "
            if y == 0 or y == st.height - 1:
                ch = "-"
            elif x == st.width // 2:
                ch = "|"
            ui.safe_addch(screen, oy + y, ox + x, ord(ch))
    for d in range(-st.paddle // 2, st.paddle // 2 + 1):
        ui.safe_addch(screen, oy + int(st.player) + d, ox + 1, ord("#"),
                      ui.color(2) | curses.A_BOLD)
        ui.safe_addch(screen, oy + int(st.cpu) + d, ox + st.width - 2, ord("#"),
                      ui.color(5) | curses.A_BOLD)
    ui.safe_addch(screen, oy + int(round(st.by)), ox + int(round(st.bx)),
                  ord("O"), ui.color(3) | curses.A_BOLD)
    ui.centered(screen, 0, "PONG  you %d : %d cpu (first to %d)" % (
        st.player_score, st.cpu_score, WIN_SCORE), ui.color(1) | curses.A_BOLD)


def play(stdscr, score_store):
    curses.curs_set(0)
    try:
        stdscr.keypad(True)
        stdscr.timeout(50)
    except curses.error:
        pass
    st = PongState()
    player_move = 0
    last = time.time()
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
        try:
            key = stdscr.getch()
        except curses.error:
            key = -1
        if key in ui.QUIT_KEYS:
            scores_mod.record_play(score_store, GAME_ID,
                                   st.player_score * 20, won=st.won)
            scores_mod.save(score_store)
            return
        elif key in ui.PAUSE_KEYS:
            if ui.pause_overlay(stdscr, TITLE) == "quit":
                return
            try:
                stdscr.timeout(50)
            except curses.error:
                pass
            last = time.time()
            continue
        if key in ui.HELP_KEYS:
            ui.show_help_overlay(stdscr, TITLE, CONTROLS)
            try:
                stdscr.timeout(50)
            except curses.error:
                pass
            last = time.time()
            continue
        if key == curses.KEY_RESIZE:
            continue
        elif key in (curses.KEY_UP, ord("w"), ord("W")):
            player_move = -1
        elif key in (curses.KEY_DOWN, ord("s"), ord("S")):
            player_move = 1
        elif key == -1:
            pass
        else:
            player_move = 0
        if time.time() - last > 0.06:
            last = time.time()
            st.step(player_move)
            if key == -1:
                pass
            if st.over:
                score = st.player_score * 20 + (100 if st.won else 0)
                entry = scores_mod.get_entry(score_store, GAME_ID)
                _, is_high = scores_mod.record_play(score_store, GAME_ID,
                                                    score, won=st.won)
                scores_mod.save(score_store)
                ui.game_over_screen(
                    stdscr, TITLE,
                    ["You beat the CPU %d:%d!" % (st.player_score, st.cpu_score)
                     if st.won else "CPU wins %d:%d. Rematch?" % (
                         st.cpu_score, st.player_score)],
                    score=score, best=max(entry["high"], score),
                    is_new_high=is_high, game_id=GAME_ID, won=st.won)
                return
            # decay movement so holding isn't required
            if key == -1:
                player_move = 0
        try:
            stdscr.clear()
        except curses.error:
            pass
        h, w = stdscr.getmaxyx()
        fw = min(st.width, w - 2)
        fh = min(st.height, h - 3)
        ox = max(0, (w - fw) // 2)
        oy = max(1, (h - fh) // 2)
        draw(stdscr, st, ox, oy)
        ui.game_footer(stdscr, CONTROLS)
        try:
            stdscr.refresh()
        except curses.error:
            pass
