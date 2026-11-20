# GameBored

GameBored: a colorful terminal arcade menu with 15 games. Frederick types
`GameBored` in a shell, picks a game, plays, and lands back at the menu.
`q`/`Esc` quits anywhere.

Built for a headless Fedora 43 Server box (SSH + local console): Python 3
standard library only (`curses`), no pip installs, runs at 80x24, survives
resizes and tiny terminals (shows a "make the window bigger" message instead
of crashing), and always restores the terminal on exit or crash.

## Install (no sudo)

```bash
git clone <this-repo> && cd gamebored
./install.sh
```

That copies the game to `~/.local/share/gamebored`, installs an executable
`GameBored` launcher (plus a lowercase `gamebored` symlink) in
`~/.local/bin` — on Fedora's default `PATH` — and adds `~/.local/bin` to
`PATH` via `~/.bashrc` if it is missing. Then:

```bash
GameBored      # or: gamebored
```

Scores live in `~/.local/share/gamebored/scores.json`.

## Uninstall

```bash
./uninstall.sh
```

## The 15 games

| # | Game | Controls |
|---|------|----------|
| 1 | Snake — eat, grow, don't crash | Arrows/WASD |
| 2 | Block Stack — Tetris-style falling blocks | Arrows move, Up rotate, Space hard-drop |
| 3 | 2048 — slide and merge to 2048 | Arrows/WASD, R restart |
| 4 | Minesweeper — 9x9, 10 mines | Arrows + Space dig, F flag |
| 5 | Tic-Tac-Toe vs computer (unbeatable-ish minimax) | Arrows + Space, or 1-9 |
| 6 | Hangman — guess the secret word | Type letters |
| 7 | Pong vs CPU — first to 5 | Up/Down or W/S |
| 8 | Invaders — shoot the descending aliens | Left/Right or A/D, Space |
| 9 | Breakout — smash every brick, 3 lives | Left/Right or A/D |
| 0 | Word Guess — Wordle-style, 6 tries | Type + Enter, Backspace |
| a | Frogger — hop across 5 lanes of traffic, 3 lives | Arrows/WASD |
| b | Simon — repeat the growing memory sequence | Watch, then press 1-4 |
| c | Sokoban — push every box onto a target (3 rooms) | Arrows/WASD push, R restart room |
| d | Connect Four — line up four vs the CPU | Left/Right + Space, or 1-7 |
| e | Flappy — flap through the pipes | Space/Up flap |

Menu: `Up/Down` + `Enter`, or shortcuts `1-9,0,a-e`. `H` opens the
High Scores table, `T` opens the Score Translator. Every game shows its
controls on screen, ends with a game-over panel (raw score AND its Bored
Points translation, best, NEW HIGH SCORE), and returns to the menu. High
scores persist per game.

Text renders of the menu and several games live in `docs/screenshots/`
(regenerate with `python3 tools/capture.py`).

## Word lists

Hangman and Word Guess draw from data files in the repo — no network fetch
at runtime, ever:

- `gamebored/data/words.txt` — 2,800+ common, family-friendly English words
  (3-8 letters) used by Hangman (4-8 letters).
- `gamebored/data/words5.txt` — 1,000+ common five-letter words used by
  Word Guess for answers and accepted guesses.

If a data file ever goes missing, the games fall back to small built-in
lists so they still run.

## Score Translator: Bored Points (BP)

Every game's raw score lives on its own scale (2048 counts merges in the
thousands, Tic-Tac-Toe counts single wins, Snake counts apples...). Bored
Points (BP) translate them all into one shared language:

**BP = raw x RATE**, with a per-game rate calibrated so a comparable effort
in any game earns a comparable pile of BP (a decent few minutes of play
lands around 1,000-1,500 BP everywhere).

| Game | Raw score meaning | Rate (BP per raw) | Decent session |
|------|-------------------|-------------------|----------------|
| Snake | apples eaten | 100 | 15 apples -> 1,500 BP |
| Block Stack | stack points (40/line, +2/piece) | 3 | 500 pts -> 1,500 BP |
| 2048 | merge points | 0.3 | 5,000 pts -> 1,500 BP |
| Minesweeper | clear points (win ~= 500-1,500) | 1.5 | 1,000 pts -> 1,500 BP |
| Tic-Tac-Toe | 100 win / 10 draw / 0 loss | 15 | win (100) -> 1,500 BP |
| Hangman | word points (~50-160 per win) | 15 | 100 pts -> 1,500 BP |
| Pong | match points (win = 200) | 7.5 | win (200) -> 1,500 BP |
| Invaders | alien points (10 x level each) | 3 | 500 pts -> 1,500 BP |
| Breakout | brick points + 200 win bonus | 3 | 500 pts -> 1,500 BP |
| Word Guess | guess points (20-120 per win) | 12.5 | 80 pts -> 1,000 BP |
| Frogger | crossing points (100 each) | 4 | 400 pts -> 1,600 BP |
| Simon | rounds cleared (best streak) | 150 | 10 rounds -> 1,500 BP |
| Sokoban | 100/box + 500/room | 2 | 800 pts -> 1,600 BP |
| Connect Four | 150 win / 25 draw / 0 loss | 10 | win (150) -> 1,500 BP |
| Flappy | pipes passed | 100 | 15 pipes -> 1,500 BP |

The rates live in `gamebored/translator.py` (`CONVERSIONS`). Every score
shown anywhere — game-over panels (`Score: 248 -> 1,240 BP`), the High
Scores table, the menu's per-game bests — shows the raw score AND its BP
translation. The High Scores screen also shows a combined all-games total
in BP. The `T` menu entry opens an interactive translator: pick a game,
type any raw number, see the BP value.

## Tests (developers)

Testing-only deps (never needed to play): `pip install -r requirements-test.txt`

```bash
python3 -m pytest tests/ -q
```

- `tests/test_logic.py` — unit tests for each game's rules (merges, minimax,
  feedback, collisions, win/lose paths) plus score-file handling.
- `tests/test_translator.py` — `unittest` checks for the Score Translator:
  every game has a positive rate, known conversions hold, typical-good
  sessions land in the same BP neighbourhood, formatting, totals.
- `tests/test_words.py` — `unittest` checks for the word lists: 2,000+
  general words, 1,000+ five-letter words, all clean/lowercase/unique,
  family-friendly, games actually use the files, no network fetch.
- `tests/test_smoke.py` — `unittest` smoke test: all 15 game modules import
  and their headless init/step logic runs (including a BFS proof that every
  Sokoban room is solvable).
- `tests/test_pty.py` — drives the real app headlessly in a pseudo-terminal
  (80x24): launches each of the 15 games from the menu, sends gameplay input,
  converts a score in the translator, quits back to the menu, and exits with
  status 0; also covers tiny-terminal and resize behavior.
