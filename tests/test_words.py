"""Unit tests for the word lists (no network fetch at runtime)."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gamebored import words as words_mod

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORDS_FILE = os.path.join(REPO, "gamebored", "data", "words.txt")
WORDS5_FILE = os.path.join(REPO, "gamebored", "data", "words5.txt")

# Words that must never appear in a family-friendly list.
BANNED = ["fuck", "shit", "bitch", "cunt", "dick", "pussy", "whore",
          "slut", "rape", "porn", "nazi", "hitler", "damn", "hell",
          "kill", "murder", "suicide", "terror"]


def read_lines(path):
    with open(path, "r", encoding="utf-8") as fh:
        return [ln.strip() for ln in fh if ln.strip()]


class TestWordLists(unittest.TestCase):
    def test_words_file_big_enough(self):
        words = read_lines(WORDS_FILE)
        self.assertGreaterEqual(len(words), 2000,
                                "need 2,000+ words, have %d" % len(words))

    def test_words_are_clean_lowercase_alpha(self):
        for w in read_lines(WORDS_FILE):
            self.assertTrue(w.isalpha(), "non-alpha word: %r" % w)
            self.assertEqual(w, w.lower(), "not lowercase: %r" % w)

    def test_words_no_duplicates(self):
        words = read_lines(WORDS_FILE)
        self.assertEqual(len(words), len(set(words)), "duplicate words found")

    def test_words_family_friendly(self):
        have = set(read_lines(WORDS_FILE))
        bad = [w for w in BANNED if w in have]
        self.assertEqual(bad, [], "banned words present: %r" % bad)

    def test_words5_big_enough_and_all_five_letters(self):
        words = read_lines(WORDS5_FILE)
        self.assertGreaterEqual(len(words), 1000,
                                "need 1,000+ 5-letter words, have %d" %
                                len(words))
        for w in words:
            self.assertEqual(len(w), 5, "not 5 letters: %r" % w)
            self.assertTrue(w.isalpha() and w == w.lower(),
                            "not clean lowercase: %r" % w)
        self.assertEqual(len(words), len(set(words)), "duplicates in words5")

    def test_words5_covered_by_general_list(self):
        general = set(read_lines(WORDS_FILE))
        missing = [w for w in read_lines(WORDS5_FILE) if w not in general]
        self.assertEqual(missing, [], "5-letter words missing: %r" % missing[:5])

    def test_loaders_return_big_lists(self):
        self.assertGreaterEqual(len(words_mod.load_words()), 2000)
        self.assertGreaterEqual(len(words_mod.load_words5()), 1000)
        for w in words_mod.load_words5():
            self.assertEqual(len(w), 5)

    def test_word_games_use_the_lists(self):
        from gamebored.games import hangman, wordle
        self.assertGreaterEqual(len(hangman.WORDS), 2000)
        for w in hangman.WORDS:
            self.assertTrue(4 <= len(w) <= 8, "bad hangman length: %r" % w)
        self.assertGreaterEqual(len(wordle.ANSWERS), 1000)
        for w in wordle.ANSWERS:
            self.assertEqual(len(w), 5, "bad wordle length: %r" % w)

    def test_no_network_fetch_at_runtime(self):
        import gamebored.words as wm
        with open(wm.__file__, "r", encoding="utf-8") as fh:
            src = fh.read()
        for token in ("urllib", "socket", "requests", "http://",
                      "https://", "urlopen"):
            self.assertNotIn(token, src,
                             "words loader must not fetch over network")


if __name__ == "__main__":
    unittest.main()
