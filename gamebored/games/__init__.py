"""Game registry: the 16 playable games."""

from . import breakout, connect4, flappy, frogger, g2048, hangman, invaders
from . import minesweeper, platformer, pong, simon, snake, sokoban, tetris
from . import tictactoe, wordle

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
    frogger,
    simon,
    sokoban,
    connect4,
    flappy,
    platformer,
]

assert len(GAMES) == 16, "GameBored ships exactly 16 games"
