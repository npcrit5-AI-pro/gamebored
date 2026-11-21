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
    from gamebored.app import build_entries, draw_menu
    draw_menu(menu, 2, {}, build_entries())
    states["menu"] = menu.text()

    # Bored Wondering with sample results (no network: canned data)
    from gamebored import wondering as wondering_mod
    wscr = FakeScreen()
    sample = [
        {"title": "Python (programming language)", "source": "wikipedia",
         "snippet": "Python is a high-level, general-purpose programming language.",
         "url": "https://en.wikipedia.org/wiki/Python_(programming_language)"},
        {"title": "Welcome to Python.org", "source": "duckduckgo",
         "snippet": "The official home of the Python Programming Language.",
         "url": "https://www.python.org/"},
        {"title": "Uv is the best thing to happen to Python", "source": "hackernews",
         "snippet": "by todsacerdoti - 312 points",
         "url": "https://news.ycombinator.com/item?id=12345678"},
    ]
    wondering_mod.draw_screen(wscr, "python", sample, {}, 0, 0, False, "python")
    states["wondering"] = wscr.text()

    # Help screen (first page, rendered statically from the real lines)
    from gamebored import extras as extras_mod
    hscr = FakeScreen()
    for i, ln in enumerate(extras_mod.build_help_lines(GAMES)[:20]):
        hscr.addstr(2 + i, 3, ln)
    states["help"] = hscr.text()

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

    from gamebored.games import connect4, flappy, frogger, simon, sokoban

    fr = frogger.new_state(seed=7)
    fr.move(0, -1)
    fr.step()
    scr = FakeScreen()
    frogger.draw(scr, fr)
    states["frogger"] = scr.text()

    sm = simon.new_state(seed=3)
    scr = FakeScreen()
    simon.draw(scr, sm, highlight=sm.seq[0])
    states["simon"] = scr.text()

    sk = sokoban.new_state(1)
    sk.move(0, 1)
    scr = FakeScreen()
    sokoban.draw(scr, sk, sk.score)
    states["sokoban"] = scr.text()

    c4 = connect4.new_state(seed=1)
    c4.drop(3, "X")
    c4.ai_move()
    scr = FakeScreen()
    connect4.draw(scr, c4)
    states["connect4"] = scr.text()

    fl = flappy.new_state(seed=2)
    for _ in range(6):
        fl.step(flap=(fl.vy > 0.5))
    scr = FakeScreen()
    flappy.draw(scr, fl)
    states["flappy"] = scr.text()

    from gamebored.games import platformer
    rn = platformer.RunState(platformer.LEVELS[12])
    for _ in range(4):
        rn.step(0.09, move=1)
    scr = FakeScreen()
    platformer.draw(scr, rn, platformer.room_label(12, len(platformer.LEVELS),
                                                   rn))
    states["runner"] = scr.text()

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
