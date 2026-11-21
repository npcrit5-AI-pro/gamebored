"""Smoke tests: every game module imports and its logic runs headless.

No curses is touched here: each game's state/step layer must work without
a terminal, which is also what makes the games unit-testable.
"""

import os
import sys
import unittest
from collections import deque

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gamebored import translator
from gamebored.games import GAMES


class TestSmoke(unittest.TestCase):
    def test_all_fifteen_import_and_register(self):
        self.assertEqual(len(GAMES), 16)
        for mod in GAMES:
            for attr in ("TITLE", "DESCRIPTION", "CONTROLS", "GAME_ID",
                         "play"):
                self.assertTrue(hasattr(mod, attr),
                                "%s missing %s" % (mod.__name__, attr))
            self.assertIn(mod.GAME_ID, translator.CONVERSIONS)
            self.assertTrue(callable(mod.play))

    def test_snake(self):
        from gamebored.games import snake
        st = snake.new_state(6, 6, seed=1)
        st.snake = [(2, 2), (1, 2), (0, 2)]
        st.direction = st.pending = snake.RIGHT
        st.food = (3, 2)
        self.assertTrue(st.step())
        self.assertEqual(st.score, 1)

    def test_tetris(self):
        from gamebored.games import tetris
        st = tetris.TetrisState(seed=0)
        st.move(0, 1)
        st.rotate_piece()
        self.assertFalse(st.over)

    def test_g2048(self):
        from gamebored.games import g2048
        st = g2048.State2048(seed=0)
        st.move("left")
        self.assertGreaterEqual(st.score, 0)

    def test_minesweeper(self):
        from gamebored.games import minesweeper
        st = minesweeper.MineState(seed=42)
        st.reveal(4, 4)
        self.assertTrue(st.started)

    def test_tictactoe(self):
        from gamebored.games import tictactoe
        st = tictactoe.TicState()
        st.human(0)
        self.assertEqual(st.board[0], "X")

    def test_hangman(self):
        from gamebored.games import hangman
        st = hangman.HangState(word="APPLE")
        self.assertTrue(st.guess("a"))

    def test_pong(self):
        from gamebored.games import pong
        st = pong.PongState(width=30, height=10)
        st.step(0)
        self.assertFalse(st.over)

    def test_invaders(self):
        from gamebored.games import invaders
        st = invaders.InvaderState(width=50, height=18, seed=0)
        st.step()
        self.assertFalse(st.over)

    def test_breakout(self):
        from gamebored.games import breakout
        st = breakout.BreakState(width=40, height=16)
        st.step(0)
        self.assertFalse(st.over)

    def test_wordle(self):
        from gamebored.games import wordle
        st = wordle.WordleState(answer="APPLE")
        st.current = "APPLE"
        self.assertTrue(st.submit())
        self.assertTrue(st.won)

    def test_frogger(self):
        from gamebored.games import frogger
        st = frogger.new_state(seed=7)
        st.move(0, -1)
        self.assertTrue(st.step())
        # hop straight to the bank: a crossing registers, no crash
        st2 = frogger.new_state(seed=7)
        for _ in range(st2.lanes + 1):
            st2.move(0, -1)
        self.assertEqual(st2.crossings, 1)
        self.assertEqual(st2.score, 100)
        # three squishes ends the run
        st3 = frogger.new_state(seed=7)
        st3.lives = 1
        st3.frog_y = 1
        lane = st3.traffic[0]
        # cars move first, so park one just upstream of the frog
        lane["cars"] = {(st3.frog_x - lane["dir"]) % st3.width}
        lane["counter"] = lane["speed"] - 1
        st3.step()
        self.assertTrue(st3.over)

    def test_simon(self):
        from gamebored.games import simon
        st = simon.new_state(seed=3)
        first = st.expected()
        self.assertIn(st.press(first), ("next", "round"))
        if not st.over and st.rounds == 0:
            # first press completed only if sequence had length 1
            pass
        # a wrong pad always ends the run
        st2 = simon.new_state(seed=3)
        wrong = (st2.expected() + 1) % 4
        self.assertEqual(st2.press(wrong), "gameover")
        self.assertTrue(st2.over)
        # repeating the full shown sequence clears a round
        st3 = simon.new_state(seed=3)
        seq = list(st3.seq)
        for pad in seq:
            result = st3.press(pad)
        self.assertEqual(result, "round")
        self.assertEqual(st3.rounds, 1)

    def test_sokoban_all_rooms_solvable(self):
        from gamebored.games import sokoban, sokoban_solver
        for level in range(len(sokoban.LEVELS)):
            solution = sokoban_solver.solve_pushes(
                sokoban.LEVELS[level], cap=30000, time_limit=3.0)
            self.assertIsNotNone(solution,
                                 "room %d looks unsolvable" % (level + 1))
        # walking into a wall does nothing
        st = sokoban.new_state(0)
        st.player = (1, 1)
        before = (st.player, st.moves)
        self.assertFalse(st.move(-1, 0))
        self.assertEqual((st.player, st.moves), before)
        st.restart()
        self.assertEqual(st.moves, 0)

    def test_connect4(self):
        from gamebored.games import connect4
        st = connect4.new_state(seed=1)
        self.assertIsNotNone(st.drop(3, "X"))
        self.assertIsNone(st.result())
        # vertical four wins
        st2 = connect4.new_state(seed=1)
        for _ in range(4):
            st2.drop(0, "X")
        self.assertEqual(st2.result(), "X")
        # AI answers a move
        st3 = connect4.new_state(seed=1)
        st3.drop(3, "X")
        self.assertIsNotNone(st3.ai_move())

    def test_flappy(self):
        from gamebored.games import flappy
        st = flappy.new_state(seed=2)
        y0 = st.bird_y
        st.step(flap=False)
        self.assertGreater(st.bird_y, y0)  # gravity pulls down
        st2 = flappy.new_state(seed=2)
        st2.step(flap=True)
        self.assertLess(st2.bird_y, float(st2.height // 2))  # flap lifts
        # a pipe right at the bird scores as it passes
        st3 = flappy.new_state(seed=2)
        st3.pipes = [[st3.bird_x, int(st3.bird_y - 1.6)]]
        st3.vy = 0.0
        st3.step(flap=True)
        self.assertGreaterEqual(st3.score, 1)
        # hitting the floor ends the flight
        st4 = flappy.new_state(seed=2)
        st4.bird_y = float(st4.height - 1)
        st4.vy = 5.0
        st4.step()
        self.assertTrue(st4.over)


def solve_sokoban(level, cap=300000):
    """BFS over (player, boxes) for one room. Returns a move list or None."""
    from gamebored.games import sokoban
    probe = sokoban.new_state(level)
    walls, targets = probe.walls, probe.targets
    start = (probe.player, frozenset(probe.boxes))

    def solved(boxes):
        return bool(boxes) and boxes <= targets

    seen = {start}
    queue = deque([(start, [])])
    while queue and len(seen) < cap:
        (player, boxes), path = queue.popleft()
        if solved(boxes):
            return path
        for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
            npos = (player[0] + dx, player[1] + dy)
            if npos in walls:
                continue
            nboxes = boxes
            if npos in boxes:
                beyond = (npos[0] + dx, npos[1] + dy)
                if beyond in walls or beyond in boxes:
                    continue
                nboxes = frozenset(
                    beyond if b == npos else b for b in boxes)
            key = (npos, nboxes)
            if key not in seen:
                seen.add(key)
                queue.append((key, path + [(dx, dy)]))
    return None


if __name__ == "__main__":
    unittest.main()
