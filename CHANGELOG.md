# GameBored Changelog

## v1.4.0 — 39 improvement rounds (on top of v1.3.0)

Every v1.3.0 feature is kept: 16 games including Runner (60 rooms,
solver-verified endless), Sokoban with all 205 rooms, room pickers with
saved `progress.json`, solver-verified endless modes, Bored Wondering,
High Scores, Score Translator, `p` pause / `?` help / `q` menu in every
game, stdlib-only curses UI at 80x24, and `install.sh`/`uninstall.sh`
with no sudo. Full suite: 129 passing (`python3 -m pytest tests -q`:
all 93 v1.3.0 tests plus 36 new).

Every existing feature is kept: 15 games, Bored Wondering keyless search,
High Scores with Bored Points, the Score Translator, categorized menu,
`p` pause / `?` help / `q` menu in every game, stdlib-only curses UI at
80x24, and `install.sh`/`uninstall.sh` with no sudo. Full suite: 113
passing (`python3 -m pytest tests -q`).

Crash and robustness fixes first (headless fuzzing, corrupted saves,
tiny/odd terminals, no-color, offline search):

- Round 1: harden `scores.get_entry` against corrupted JSON values — junk
  `high`/`plays`/`wins` (strings, lists, Infinity) now read as 0 instead
  of raising.
- Round 2: atomic `scores.save` via tmp file plus rename, so a crash
  mid-write can never leave half a `scores.json` behind.
- Round 3: harden the Bored Points translator against NaN, Infinity, and
  junk input; negative totals print correctly.
- Round 4: ignore out-of-bounds Minesweeper reveal and flag instead of
  raising `IndexError`.
- Round 5: reject illegal Tic-Tac-Toe moves (out of range, wrong type)
  instead of crashing.
- Round 6: Hangman ignores non-string and multi-letter guesses.
- Round 7: 2048 ignores bad directions and malformed boards instead of
  raising `ValueError`.
- Round 8: clamp the Sokoban start room into the valid range (kept
  through the v1.3.0 rebase: all 205 rooms intact).
- Round 9: `safe_addstr` and `safe_addch` tolerate junk input (non-string
  text, out-of-range codes) and catch `TypeError`/`ValueError` too.
- Round 10: cap search responses at 2 MiB per source and tolerate
  malformed result payloads; `_clean` keeps `None` as `""`.
- Round 11: Connect Four rejects bad columns and out-of-range cells.
- Round 12: Frogger clamps tiny board dimensions.
- Round 13: clamp Bored Wondering detail scrolling to the content
  (extracted `_detail_lines` helper, hardened to junk fields).
- Round 14: clamp High Scores scrolling to the content.
- Round 15: word loader ignores garbage and overlong lines.
- Round 16: menu tolerates empty entries and non-key input; hotkeys stay
  unique.
- Round 18: Snake clamps board size and validates turns.
- Round 19: Flappy clamps degenerate dimensions and gap.
- Round 20: full-suite checkpoint — green, no changes needed.
- Round 23: normalize word-game answers to uppercase so a lowercase or
  overlong answer can never make a round unwinnable.
- Round 24: Pong ignores non-numeric step input.
- Round 25: Breakout ignores non-numeric paddle input.
- Round 26: Invaders coerces level to a sane integer (a junk level used
  to corrupt the score type).
- Round 27: Tetris ignores bad moves after game over / with no piece.
- Round 30: menu loop exits cleanly with an empty registry.
- Round 33: lock in headless draw fuzz at odd terminal sizes (all 16
  games at 80x24 down to 20x6, Runner included).
- Round 34: screenshot capture renders every screen (menu, wondering,
  help, all 16 games) as a regression test.

Usability and polish:

- Round 17: installer preflight checks `python3` (>= 3.8) and curses
  before installing.
- Round 21: menu subtitle reads the version from the package instead of
  a hardcoded string.
- Round 22: unknown CLI flags print usage (exit 2) instead of launching
  the game.
- Round 28: menu always hides the cursor after a game returns (quitting
  Bored Wondering or pausing out of Word Guess used to leave it visible).
- Round 29: game-over panel says "any key: back to menu", matching the
  actual behavior.

Installer and tests:

- Round 31: add installer round-trip test with a scratch HOME
  (`tests/test_install.py`).
- Round 32: high scores survive uninstall and reinstall — `uninstall.sh`
  backs up `scores.json`, `install.sh` restores it.
- Round 35: harden `progress.json` save/load against corruption —
  atomic saves, dict guards, junk levels can never skip ahead, locked
  endless stays locked.
- Round 36: Runner ignores junk rows, steps, and levels (bad `new_state`
  levels clamp into the 60-room set).
- Round 37: Sokoban and Runner room pickers survive key mashing and junk
  progress (600-key fuzz each, locked endless stays unpickable).
- Round 38: CLI `--list` covers all sixteen games; Runner has a BP rate.
- Round 39: refresh the menu screenshot for sixteen games and v1.4.0.

Final: version stays 1.4.0 (`gamebored/__init__.py`, search `USER_AGENT`,
README, screenshots), full suite green (129 passed: all 93 v1.3.0 tests
plus 36 new), a manual `install.sh`/`uninstall.sh` round-trip verified
with a scratch HOME, and `python3 -m gamebored --list` shows 16 games
including Runner.

## v1.2.0 — polished menu, Bored Wondering search, pause/help everywhere
## v1.1.0 — fifteen games, bigger word lists, Bored Points Score Translator
## v1.0.0 — colorful curses arcade with 10 games, installer, tests
