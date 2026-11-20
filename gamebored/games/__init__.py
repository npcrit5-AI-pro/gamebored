"""Game registry: the 15 playable games."""

from . import breakout, connect4, flappy, frogger, g2048, hangman, invaders
from . import minesweeper, pong, simon, snake, sokoban, tetris, tictactoe
from . import wordle

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
]

assert len(GAMES) == 15, "GameBored ships exactly 15 games"
