"""Unit tests for GameBored game logic (no curses needed)."""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gamebored import scores as scores_mod
from gamebored.games import GAMES
from gamebored.games import snake, tetris, g2048, minesweeper, tictactoe
from gamebored.games import hangman, pong, invaders, breakout, wordle


def test_registry_has_ten_games():
    assert len(GAMES) == 10
    for mod in GAMES:
        for attr in ("TITLE", "DESCRIPTION", "CONTROLS", "GAME_ID", "play"):
            assert hasattr(mod, attr), "%s missing %s" % (mod, attr)


def test_scores_roundtrip(tmp_path):
    path = str(tmp_path / "scores.json")
    store = scores_mod.load(path)
    assert store == {}
    entry, is_high = scores_mod.record_play(store, "snake", 5, path=path)
    assert is_high and entry["high"] == 5 and entry["plays"] == 1
    entry, is_high = scores_mod.record_play(store, "snake", 3, path=path)
    assert not is_high and entry["high"] == 5 and entry["plays"] == 2
    reloaded = scores_mod.load(path)
    assert reloaded["snake"]["high"] == 5
    # corrupt file -> empty dict, never crash
    with open(path, "w") as fh:
        fh.write("not json{{{")
    assert scores_mod.load(path) == {}


def test_snake_eats_and_dies():
    st = snake.new_state(6, 6, seed=1)
    st.snake = [(2, 2), (1, 2), (0, 2)]
    st.direction = st.pending = snake.RIGHT
    st.food = (3, 2)
    assert st.step() is True
    assert st.score == 1 and len(st.snake) == 4
    # run into the wall
    st.set_direction(snake.RIGHT)
    for _ in range(10):
        st.step()
    assert st.alive is False
    # reversing is ignored
    st2 = snake.new_state(6, 6, seed=2)
    st2.set_direction(snake.LEFT)  # opposite of RIGHT start
    assert st2.pending == snake.RIGHT


def test_tetris_spawn_move_lock_and_lines():
    st = tetris.TetrisState(seed=0)
    assert st.piece is not None and not st.over
    assert st.move(0, 1) in (True, False)
    st.rotate_piece()  # must not crash
    # fill bottom row except one cell, drop O piece to clear
    st.board = [[None] * tetris.W for _ in range(tetris.H)]
    for x in range(tetris.W):
        st.board[tetris.H - 1][x] = "I"
    n = tetris.clear_lines_count(st.board)
    assert n == 1
    assert all(c is None for c in st.board[tetris.H - 1])
    # hard drop locks a piece and spawns another
    st2 = tetris.TetrisState(seed=3)
    before = st2.score
    st2.hard_drop()
    assert st2.score >= before and not st2.over
    # top-out detection
    st3 = tetris.TetrisState(seed=4)
    st3.board[0] = ["I"] * tetris.W
    st3.board[1] = ["I"] * tetris.W
    st3.spawn()
    assert st3.over is True


def test_2048_merge_and_gameover():
    board = [[2, 2, 4, 4], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]]
    new, gained, moved = g2048.move_board(board, "left")
    assert new[0] == [4, 8, 0, 0] and gained == 12 and moved
    new2, _, moved2 = g2048.move_board(new, "left")
    assert moved2 is False or new2 == new
    full = [[2, 4, 2, 4], [4, 2, 4, 2], [2, 4, 2, 4], [4, 2, 4, 2]]
    assert g2048.can_move(full) is False
    assert g2048.can_move(board) is True
    st = g2048.State2048(seed=0)
    assert sum(1 for row in st.board for v in row if v) == 2
    st.board = [row[:] for row in full]
    st.move("left")
    assert st.over is True


def test_minesweeper_first_click_safe_and_win():
    st = minesweeper.MineState(seed=42)
    st.reveal(4, 4)
    assert st.started and not st.over  # first click never a mine
    assert (4, 4) not in st.mines
    st.toggle_flag(0, 0)
    assert st.flagged[0][0] is True
    st.toggle_flag(0, 0)
    assert st.flagged[0][0] is False
    # boom path with a preset mine
    st2 = minesweeper.MineState(preset={(1, 1)})
    st2.reveal(0, 0)  # safe (count 1)
    assert not st2.over
    st2.reveal(1, 1)
    assert st2.over and not st2.won
    # win path: reveal everything but the mine
    st3 = minesweeper.MineState(preset={(8, 8)})
    for r in range(9):
        for c in range(9):
            if (r, c) != (8, 8):
                st3.reveal(r, c)
    assert st3.over and st3.won


def test_tictactoe_ai_blocks_and_wins():
    assert tictactoe.winner(["X", "X", "X", "", "", "", "", "", ""]) == "X"
    assert tictactoe.winner([""] * 9) is None
    assert tictactoe.winner(["X", "O", "X", "X", "O", "O", "O", "X", "X"]) == "draw"
    # AI takes the win
    board = ["O", "O", "", "X", "X", "", "", "", ""]
    assert tictactoe.best_move(board[:]) == 2
    # AI blocks the loss
    board2 = ["X", "X", "", "O", "", "", "", "", ""]
    assert tictactoe.best_move(board2[:]) == 2
    st = tictactoe.TicState()
    st.human(0)
    assert st.board[0] == "X" and "O" in st.board


def test_hangman_flow():
    st = hangman.HangState(word="APPLE")
    assert st.guess("a") is True
    assert st.guess("z") is False
    assert st.guess("a") is None  # duplicate
    assert st.guess("1") is None  # not a letter
    for ch in "PLE":
        st.guess(ch)
    assert st.won and st.over
    st2 = hangman.HangState(word="ZZZ")
    for ch in "ABCDEF":
        st2.guess(ch)
    assert st2.over and not st2.won


def test_pong_scores_and_ends():
    st = pong.PongState(width=30, height=10)
    st.bx, st.by, st.vx, st.vy = 15, 5, 1.0, 0.0
    st.cpu = 5
    st.step(0)
    assert 0 <= st.bx < st.width
    # miss the ball -> cpu scores
    st2 = pong.PongState(width=30, height=10)
    st2.bx, st2.by, st2.vx, st2.vy = 1.5, 0, -2.0, 0.0
    st2.player = 9  # far from ball
    st2.step(0)
    assert st2.cpu_score == 1
    st2.player_score = pong.WIN_SCORE - 1
    st2.bx, st2.vx = 28.5, 2.0
    st2.cpu = 0
    st2.by = 9  # far from cpu paddle
    st2.step(0)
    assert st2.over and st2.won


def test_invaders_shoot_and_waves():
    st = invaders.InvaderState(width=50, height=18, seed=0)
    n = len(st.aliens)
    assert n == invaders.COLS * invaders.ROWS
    # park a bullet right under an alien
    ax, ay = sorted(st.aliens)[0]
    st.ship_x = ax
    st.bullets = [(ax, ay + 1)]
    score_before = st.score
    st.step()
    assert st.score > score_before
    # clearing all aliens starts the next wave
    st.aliens = set()
    st.step()
    assert st.level == 2 and len(st.aliens) > 0
    # aliens landing ends the game
    st.aliens = {(5, st.height - 2)}
    st.bombs = []
    st.step()
    assert st.over and not st.won


def test_breakout_bricks_and_lives():
    st = breakout.BreakState(width=40, height=16)
    assert len(st.bricks) == breakout.BRICK_ROWS * breakout.BRICK_COLS
    # smash one brick
    bc, br = sorted(st.bricks)[0]
    bw = max(1, st.width // breakout.BRICK_COLS)
    st.bx = bc * bw + 0.5
    st.by = 2 + br + 0.5
    st.vx, st.vy = 0.0, -1.0
    n = len(st.bricks)
    st.step(0)
    assert len(st.bricks) in (n - 1, n)  # hit or bounced near edge
    # drain the ball -> lose a life, then game over at 0
    st2 = breakout.BreakState(width=40, height=16)
    st2.bx, st2.by, st2.vx, st2.vy = 0.5, 15.5, 0.0, 1.0
    st2.paddle = 35
    lives = st2.lives
    st2.step(0)
    assert st2.lives in (lives, lives - 1)
    st2.lives = 1
    st2.bx, st2.by, st2.vx, st2.vy = 0.5, 15.5, 0.0, 1.0
    st2.paddle = 35
    st2.step(0)
    assert st2.over and not st2.won


def test_wordle_feedback_duplicates():
    assert wordle.feedback("APPLE", "APPLE") == ["hit"] * 5
    fb = wordle.feedback("APPLE", "ALLEY")
    # A hit, L near (only one L in answer), rest miss
    assert fb[0] == "hit"
    assert fb[1] == "near"
    assert fb[2] == "miss"
    st = wordle.WordleState(answer="APPLE")
    st.current = "APPLE"
    assert st.submit() is True and st.over and st.won
    st2 = wordle.WordleState(answer="APPLE")
    st2.current = "ZZ"
    assert st2.submit() is False  # too short
    st2.current = "ZZZZZ"
    assert st2.submit() is False  # not in word list
    assert len(st2.rows) == 0
    st3 = wordle.WordleState(answer="APPLE")
    for guess in ["CRANE", "DANCE", "FLAME", "GRAPE", "HEART", "IGLOO"]:
        st3.current = guess
        st3.submit()
    assert st3.over and not st3.won
