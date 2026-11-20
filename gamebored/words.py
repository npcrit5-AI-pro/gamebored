"""Word lists for the word games (Hangman, Word Guess).

Words live in plain data files next to this module (gamebored/data/*.txt),
one lowercase word per line, so the games never fetch anything over the
network at runtime. If a data file is missing (e.g. a partial install),
each loader falls back to a small built-in list so the game still runs.
"""

import os

_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
_WORDS_FILE = os.path.join(_DATA_DIR, "words.txt")
_WORDS5_FILE = os.path.join(_DATA_DIR, "words5.txt")

_FALLBACK_WORDS = [
    "PYTHON", "ROCKET", "PIZZA", "DRAGON", "CASTLE", "ROBOT", "PLANET",
    "TIGER", "BANANA", "GUITAR", "PENGUIN", "VOLCANO", "BRIDGE", "CLOUD",
    "DESERT", "EAGLE", "FOREST", "GALAXY", "HARBOR", "ISLAND", "JUNGLE",
    "KOALA", "LEMON", "MAGNET", "NINJA", "OCEAN", "PARROT", "QUEEN",
    "RAINBOW", "SUNSET", "TURTLE", "UNICORN", "VIOLIN", "WHALE", "ZEBRA",
    "APPLE", "BALLOON", "CIRCUS", "DOLPHIN", "ELEPHANT", "FROGGY",
]

_FALLBACK_WORDS5 = [
    "APPLE", "BRAVE", "CRANE", "DANCE", "EAGLE", "FLAME", "GRAPE",
    "HEART", "IGLOO", "JUICE", "KOALA", "LEMON", "MAGIC", "NIGHT",
    "OCEAN", "PIANO", "QUEEN", "RIVER", "SNAKE", "TIGER", "ULTRA",
    "VIVID", "WHALE", "YOUTH", "ZEBRA", "CHAIR", "DREAM", "EARTH",
    "FROST", "GIANT", "HORSE", "IVORY", "JELLY", "KNEEL", "LIGHT",
    "MANGO", "NURSE", "ORBIT", "PARTY", "QUICK", "ROBOT", "SHINE",
    "TOAST", "UNDER", "VOICE", "WATER", "YACHT", "MUSIC", "HAPPY",
    "SUNNY", "CLOUD", "BEACH", "SMILE", "LAUGH", "STORM", "FOREST",
]


def _read_word_file(path):
    words = []
    try:
        with open(path, "r", encoding="utf-8") as fh:
            for line in fh:
                word = line.strip().lower()
                if word and word.isalpha():
                    words.append(word)
    except OSError:
        return []
    # de-duplicate while keeping file order
    seen = set()
    unique = []
    for word in words:
        if word not in seen:
            seen.add(word)
            unique.append(word)
    return unique


def load_words(min_len=1, max_len=99):
    """All common words (lowercase), optionally filtered by length."""
    words = _read_word_file(_WORDS_FILE)
    if not words:
        words = [w.lower() for w in _FALLBACK_WORDS]
    return [w for w in words if min_len <= len(w) <= max_len]


def load_words_upper(min_len=1, max_len=99):
    """Uppercase variant for games that display in caps (Hangman)."""
    return [w.upper() for w in load_words(min_len, max_len)]


def load_words5():
    """Five-letter words for Word Guess (uppercase)."""
    words = _read_word_file(_WORDS5_FILE)
    if not words:
        return list(_FALLBACK_WORDS5)
    fives = [w.upper() for w in words if len(w) == 5]
    return fives or list(_FALLBACK_WORDS5)
