"""Wordle-style word guess: 6 tries to find the 5-letter word."""

import curses
import random

from .. import scores as scores_mod
from .. import ui

TITLE = "Word Guess"
DESCRIPTION = "Wordle-style: 6 tries"
CONTROLS = "Type letters | Enter submit | Backspace delete | q/Esc quit"
GAME_ID = "wordle"
WORD_LEN = 5
TRIES = 6

ANSWERS = [
    "APPLE", "BRAVE", "CRANE", "DANCE", "EAGLE", "FLAME", "GRAPE",
    "HEART", "IGLOO", "JUICE", "KOALA", "LEMON", "MAGIC", "NIGHT",
    "OCEAN", "PIANO", "QUEEN", "RIVER", "SNAKE", "TIGER", "ULTRA",
    "VIVID", "WHALE", "YOUTH", "ZEBRA", "CHAIR", "DREAM", "EARTH",
    "FROST", "GIANT", "HORSE", "IVORY", "JELLY", "KNEEL", "LIGHT",
    "MANGO", "NURSE", "ORBIT", "PARTY", "QUICK", "ROBOT", "SHINE",
    "TOAST", "UNDER", "VOICE", "WATER", "YACHT", "MUSIC", "HAPPY",
    "SUNNY", "CLOUD", "BEACH", "SMILE", "LAUGH", "STORM", "FOREST",
]
ALLOWED = set(ANSWERS) | {
    "CRATE", "SLATE", "TRACE", "AUDIO", "RAISE", "ADIEU", "STARE",
    "ABOUT", "ABOVE", "ACTOR", "ACUTE", "ADMIT", "ADOPT", "ADULT",
    "AFTER", "AGAIN", "AGENT", "AGREE", "AHEAD", "ALARM", "ALBUM",
    "ALERT", "ALIKE", "ALIVE", "ALLOW", "ALONE", "ALONG", "ALOUD",
    "ALTAR", "AMBER", "AMEND", "ANGEL", "ANGER", "ANGLE", "ANGRY",
    "ANKLE", "APART", "ARENA", "ARGUE", "ARISE", "ARMOR", "AROMA",
    "ARROW", "ASIDE", "ASSET", "AVOID", "AWAKE", "AWARD", "AWARE",
    "BADGE", "BASIC", "BEARD", "BEAST", "BENCH", "BERRY", "BIRTH",
    "BLACK", "BLADE", "BLAME", "BLANK", "BLAST", "BLEND", "BLESS",
    "BLIND", "BLOCK", "BLOOD", "BOARD", "BONUS", "BOOST", "BOOTH",
    "BOUND", "BRAIN", "BRAND", "BREAD", "BREAK", "BRICK", "BRIEF",
    "BRING", "BROAD", "BROKE", "BROWN", "BRUSH", "BUILD", "BUILT",
    "BUNCH", "BUYER", "CABIN", "CABLE", "CANDY", "CARGO", "CARRY",
    "CATCH", "CAUSE", "CHAIN", "CHARM", "CHART", "CHASE", "CHEAP",
    "CHECK", "CHEESE", "CHERRY", "CHEST", "CHIEF", "CHILD", "CHOICE",
    "CHOOSE", "CHUNK", "CIVIL", "CLAIM", "CLASS", "CLEAN", "CLEAR",
    "CLIMB", "CLOCK", "CLOSE", "CLOTH", "COACH", "COAST", "COLOR",
    "COMET", "CORNER", "COUCH", "COULD", "COUNT", "COURT", "COVER",
    "CRACK", "CRASH", "CRAZY", "CREAM", "CRIME", "CRISP", "CROSS",
    "CROWD", "CROWN", "CRUDE", "CRUSH", "CURVE", "CYCLE", "DAILY",
}


def feedback(answer, guess):
    """Return list of 'hit'/'near'/'miss' per letter (handles duplicates)."""
    res = ["miss"] * WORD_LEN
    counts = {}
    for ch in answer:
        counts[ch] = counts.get(ch, 0) + 1
    for i in range(WORD_LEN):
        if guess[i] == answer[i]:
            res[i] = "hit"
            counts[guess[i]] -= 1
    for i in range(WORD_LEN):
        if res[i] == "miss" and counts.get(guess[i], 0) > 0:
            res[i] = "near"
            counts[guess[i]] -= 1
    return res


class WordleState:
    def __init__(self, answer=None, seed=None):
        rng = random.Random(seed)
        self.answer = answer or rng.choice(ANSWERS)
        self.rows = []  # (guess, feedback)
        self.current = ""
        self.over = False
        self.won = False
        self.message = ""

    def type_letter(self, ch):
        if self.over:
            return
        if len(self.current) < WORD_LEN and ch.isalpha():
            self.current += ch.upper()

    def backspace(self):
        self.current = self.current[:-1]

    def submit(self):
        if self.over:
            return False
        if len(self.current) != WORD_LEN:
            self.message = "Need %d letters!" % WORD_LEN
            return False
        if self.current not in ALLOWED and self.current != self.answer:
            self.message = "Not in word list!"
            return False
        fb = feedback(self.answer, self.current)
        self.rows.append((self.current, fb))
        self.current = ""
        self.message = ""
        if all(f == "hit" for f in fb):
            self.over = True
            self.won = True
        elif len(self.rows) >= TRIES:
            self.over = True
            self.won = False
        return True


def draw(screen, st):
    h, w = screen.getmaxyx()
    ui.centered(screen, 1, "WORD GUESS (%d tries)" % TRIES,
                ui.color(2) | curses.A_BOLD)
    y0 = 3
    for r in range(TRIES):
        cells = []
        if r < len(st.rows):
            guess, fb = st.rows[r]
        elif r == len(st.rows):
            guess, fb = st.current.ljust(WORD_LEN), [None] * WORD_LEN
        else:
            guess, fb = " " * WORD_LEN, [None] * WORD_LEN
        x0 = max(0, (w - WORD_LEN * 4) // 2)
        for i in range(WORD_LEN):
            ch = guess[i] if i < len(guess) else " "
            attr = 0
            if fb and fb[i] == "hit":
                attr = ui.color(8) | curses.A_BOLD
            elif fb and fb[i] == "near":
                attr = ui.color(9) | curses.A_BOLD
            elif fb and fb[i] == "miss":
                attr = curses.A_DIM
            ui.safe_addstr(screen, y0 + r, x0 + i * 4, "[%s]" % ch, attr)
    msg_y = y0 + TRIES + 1
    if st.message:
        ui.centered(screen, msg_y, st.message, ui.color(5) | curses.A_BOLD)
    else:
        ui.centered(screen, msg_y, "green = right spot, yellow = in word",
                    ui.color(7))


def play(stdscr, score_store):
    curses.curs_set(1)
    try:
        stdscr.keypad(True)
        stdscr.timeout(-1)
    except curses.error:
        pass
    st = WordleState()
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
        ui.footer(stdscr, CONTROLS)
        try:
            stdscr.refresh()
        except curses.error:
            pass
        if st.over:
            try:
                curses.curs_set(0)
            except curses.error:
                pass
            score = (TRIES - len(st.rows) + 1) * 20 if st.won else 0
            entry = scores_mod.get_entry(score_store, GAME_ID)
            _, is_high = scores_mod.record_play(score_store, GAME_ID, score,
                                                won=st.won)
            scores_mod.save(score_store)
            ui.game_over_screen(
                stdscr, TITLE,
                ["Brilliant! The word was %s" % st.answer if st.won
                 else "The word was: %s" % st.answer],
                score=score, best=max(entry["high"], score),
                is_new_high=is_high)
            return
        try:
            key = stdscr.getch()
        except curses.error:
            key = -1
        if key in ui.QUIT_KEYS:
            try:
                curses.curs_set(0)
            except curses.error:
                pass
            return
        elif key in (10, 13, curses.KEY_ENTER):
            st.submit()
        elif key in (curses.KEY_BACKSPACE, 127, 8):
            st.backspace()
        elif 0 <= key <= 255 and chr(key).isalpha():
            st.type_letter(chr(key))
