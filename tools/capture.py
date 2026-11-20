"""Render GameBored screens headlessly to text files (artifacts + docs).

Each game's draw function only uses addstr/addch/clear/getmaxyx, so we can
render representative mid-game states onto a FakeScreen at 80x24 without
curses. Used to prove rendering works and to produce screenshots.
Usage: python tools/capture.py [out_dir]
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gamebored.games import GAMES  # noqa: E402


class FakeScreen:
    def __init__(self, h=24, w=80):
        self.h = h
        self.w = w
        self.buf = [[" "] * w for _ in range(h)]

    def getmaxyx(self):
        return (self.h, self.w)

    def clear(self):
        self.buf = [[" "] * self.w for _ in range(self.h)]

    def refresh(self):
        pass

    def addstr(self, y, x, text, attr=0):
        if y < 0 or y >= self.h:
            return
        for i, ch in enumerate(str(text)):
            if 0 <= x + i < self.w:
                self.buf[y][x + i] = ch

    def addch(self, y, x, ch, attr=0):
        if 0 <= y < self.h and 0 <= x < self.w:
            if isinstance(ch, int):
                ch = chr(ch)
            self.buf[y][x] = ch

    def text(self):
        return "\n".join("".join(row).rstrip() for row in self.buf).rstrip() + "\n"


def build_states():
    from gamebored.games import (snake, tetris, g2048, minesweeper, tictactoe,
                                 hangman, pong, invaders, breakout, wordle)
    from gamebored import ui

    states = {}

    menu = FakeScreen()
    from gamebored import scores as scores_mod
    from gamebored.app import draw_menu
    draw_menu(menu, 2, {})
    states["menu"] = menu.text()

    st = snake.SnakeState(20, 14, seed=7)
    for _ in range(6):
        st.step()
    scr = FakeScreen()
    snake.draw(scr, st)
    ui.footer(scr, snake.CONTROLS)
    states["snake"] = scr.text()

    tst = tetris.TetrisState(seed=1)
    for _ in range(8):
        tst.move(0, 1)
    scr = FakeScreen()
    tetris.draw(scr, tst)
    ui.footer(scr, tetris.CONTROLS)
    states["tetris"] = scr.text()

    g = g2048.State2048(seed=1)
    g.move("left")
    g.move("up")
    scr = FakeScreen()
    g2048.draw(scr, g)
    states["g2048"] = scr.text()

    m = minesweeper.MineState(seed=9)
    m.reveal(4, 4)
    m.toggle_flag(0, 0)
    scr = FakeScreen()
    minesweeper.draw(scr, m, (4, 5))
    states["minesweeper"] = scr.text()

    t = tictactoe.TicState()
    t.human(0)
    t.human(8)
    scr = FakeScreen()
    tictactoe.draw(scr, t)
    states["tictactoe"] = scr.text()

    hg = hangman.HangState(word="PYTHON")
    hg.guess("P")
    hg.guess("Z")
    hg.guess("Y")
    scr = FakeScreen()
    hangman.draw(scr, hg)
    states["hangman"] = scr.text()

    p = pong.PongState(width=60, height=18)
    for _ in range(10):
        p.step(0)
    scr = FakeScreen()
    pong.draw(scr, p, 10, 3)
    states["pong"] = scr.text()

    iv = invaders.InvaderState(50, 16, seed=2)
    iv.step(1, True)
    for _ in range(6):
        iv.step(0, False)
    scr = FakeScreen()
    invaders.draw(scr, iv, 15, 4)
    states["invaders"] = scr.text()

    b = breakout.BreakState(50, 16)
    for _ in range(8):
        b.step(1)
    scr = FakeScreen()
    breakout.draw(scr, b, 15, 4)
    states["breakout"] = scr.text()

    wd = wordle.WordleState(answer="CRANE")
    wd.current = "CRATE"
    wd.submit()
    wd.current = "CRA"
    scr = FakeScreen()
    wordle.draw(scr, wd)
    states["wordle"] = scr.text()

    return states


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "docs/screenshots"
    os.makedirs(out, exist_ok=True)
    states = build_states()
    for name, text in states.items():
        path = os.path.join(out, name + ".txt")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
        print("wrote %s" % path)


if __name__ == "__main__":
    main()
