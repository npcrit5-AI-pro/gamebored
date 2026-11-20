# GameBored

GameBored: a colorful terminal arcade menu with 10 games. Frederick types
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

## The 10 games

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

Menu: `Up/Down` + `Enter`, or shortcuts `1-9,0`. Every game shows its
controls on screen, ends with a game-over panel (score, best, NEW HIGH
SCORE), and returns to the menu. High scores persist per game.

Text renders of the menu and several games live in `docs/screenshots/`
(regenerate with `python3 tools/capture.py`).

## Tests (developers)

Testing-only deps (never needed to play): `pip install -r requirements-test.txt`

```bash
python3 -m pytest tests/ -q
```

- `tests/test_logic.py` — unit tests for each game's rules (merges, minimax,
  feedback, collisions, win/lose paths) plus score-file handling.
- `tests/test_pty.py` — drives the real app headlessly in a pseudo-terminal
  (80x24): launches each of the 10 games from the menu, sends gameplay input,
  quits back to the menu, and exits with status 0; also covers tiny-terminal
  and resize behavior.
