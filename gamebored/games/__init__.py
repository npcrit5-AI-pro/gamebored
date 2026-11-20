"""Game registry: the ~10 playable games."""

from . import breakout, g2048, hangman, invaders, minesweeper, pong, snake
from . import tetris, tictactoe, wordle

GAMES = [
    snake,
    tetris,
    g2048,
    minesweeper,
    tictactoe,
    hangman,
    pong,
    invaders,
    breakout,
    wordle,
]

assert len(GAMES) == 10, "GameBored ships exactly 10 games"
