"""Hangman: guess the secret word before the drawing is finished."""

import curses
import random

from .. import scores as scores_mod
from .. import ui
from .. import words as words_mod

TITLE = "Hangman"
DESCRIPTION = "Guess the secret word"
CONTROLS = "Type letters a-z | p pause | ? help | q menu"
GAME_ID = "hangman"
CATEGORY = "CLASSIC"
MAX_WRONG = 6

# 2,800+ common words from gamebored/data/words.txt (4-8 letters).
# Falls back to a small built-in list if the data file is missing.
WORDS = words_mod.load_words_upper(4, 8) or [
    "PYTHON", "ROCKET", "PIZZA", "DRAGON", "CASTLE", "ROBOT", "PLANET",
    "TIGER", "BANANA", "GUITAR", "PENGUIN", "VOLCANO", "BRIDGE", "CLOUD",
    "DESERT", "EAGLE", "FOREST", "GALAXY", "HARBOR", "ISLAND", "JUNGLE",
    "KOALA", "LEMON", "MAGNET", "NINJA", "OCEAN", "PARROT", "QUEEN",
    "RAINBOW", "SUNSET", "TURTLE", "UNICORN", "VIOLIN", "WHALE", "ZEBRA",
    "APPLE", "BALLOON", "CIRCUS", "DOLPHIN", "ELEPHANT", "FROGGY",
]

STAGES = [
    "",
    "  O  ",
    "  O  \n  |  ",
    "  O  \n /|  ",
    "  O  \n /|\\ ",
    "  O  \n /|\\ \n /   ",
    "  O  \n /|\\ \n / \\ ",
]


def mask_word(word, guessed):
    return " ".join(ch if ch in guessed else "_" for ch in word)


def is_won(word, guessed):
    return all(ch in guessed for ch in word)


class HangState:
    def __init__(self, word=None, seed=None):
        rng = random.Random(seed)
        if not isinstance(word, str) or not word.isalpha():
            word = None
        self.word = (word or rng.choice(WORDS)).upper()
        self.guessed = set()
        self.wrong = 0

    def guess(self, letter):
        if not isinstance(letter, str):
            return None
        letter = letter.upper()
        if len(letter) != 1 or not letter.isalpha():
            return None
        if letter in self.guessed:
            return None
        self.guessed.add(letter)
        if letter not in self.word:
            self.wrong += 1
            return False
        return True

    @property
    def over(self):
        return self.wrong >= MAX_WRONG or is_won(self.word, self.guessed)

    @property
    def won(self):
        return is_won(self.word, self.guessed)


def draw(screen, st):
    h, w = screen.getmaxyx()
    ui.centered(screen, 1, "HANGMAN", ui.color(3) | curses.A_BOLD)
    stage = STAGES[min(st.wrong, MAX_WRONG)].split("\n")
    y0 = 3
    for i, line in enumerate(stage):
        ui.centered(screen, y0 + i, line, ui.color(5) | curses.A_BOLD)
    ui.centered(screen, y0 + 4, "+---+", ui.color(7))
    ui.centered(screen, y0 + 8, mask_word(st.word, st.guessed),
                ui.color(1) | curses.A_BOLD)
    guessed = "Guessed: " + (" ".join(sorted(st.guessed)) if st.guessed else "-")
    ui.centered(screen, y0 + 10, guessed, ui.color(7))
    ui.centered(screen, y0 + 11, "Wrong: %d/%d" % (st.wrong, MAX_WRONG),
                ui.color(5))


def play(stdscr, score_store):
    curses.curs_set(0)
    try:
        stdscr.keypad(True)
        stdscr.timeout(-1)
    except curses.error:
        pass
    st = HangState()
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
            stdscr.clear()
        except curses.error:
            pass
        draw(stdscr, st)
        ui.game_footer(stdscr, CONTROLS + " | word: %d letters" % len(st.word))
        try:
            stdscr.refresh()
        except curses.error:
            pass
        if st.over:
            score = (MAX_WRONG - st.wrong) * 20 + len(st.word) * 5 if st.won else 0
            entry = scores_mod.get_entry(score_store, GAME_ID)
            _, is_high = scores_mod.record_play(score_store, GAME_ID, score,
                                                won=st.won)
            scores_mod.save(score_store)
            ui.game_over_screen(
                stdscr, TITLE,
                ["You guessed it: %s!" % st.word if st.won
                 else "The word was: %s" % st.word],
                won=st.won,
                score=score, best=max(entry["high"], score),
                is_new_high=is_high, game_id=GAME_ID)
            return
        try:
            key = stdscr.getch()
        except curses.error:
            key = -1
        if key in ui.QUIT_KEYS:
            return
        elif key in ui.PAUSE_KEYS:
            if ui.pause_overlay(stdscr, TITLE) == "quit":
                return
            continue
        if key in ui.HELP_KEYS:
            ui.show_help_overlay(stdscr, TITLE, CONTROLS)
            continue
        if key == curses.KEY_RESIZE:
            continue
        if 0 <= key <= 255:
            ch = chr(key)
            if ch.isalpha():
                st.guess(ch)
