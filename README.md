# GameBored v1.4.0

GameBored: a colorful terminal arcade menu with 16 games plus Bored
Wondering, a keyless web search inside the app. Frederick types
`GameBored` in a shell, picks a game, plays, and lands back at the menu.
`q`/`Esc` quits anywhere, `p` pauses, `?` helps.

Built for a headless Fedora 43 Server box (SSH + local console): Python 3
standard library only (`curses` + `urllib`), no pip installs, runs at 80x24,
survives resizes and tiny terminals (shows a "make the window bigger"
message instead of crashing), and always restores the terminal on exit or
crash. No color? Everything still works in plain text.

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

## The menu

Games are grouped by category (ACTION / PUZZLE / CLASSIC) with a
highlighted selection, per-game best scores translated into Bored Points,
a combined BP total, and a bottom bar that always shows the keys. Move with
`Up/Down` (or `j/k`), open with `Enter`, jump straight there with a
hotkey, type `/` to filter the list, and your last pick is remembered
next launch.

| Hotkey | Entry | Controls |
|--------|-------|----------|
| 1 | Snake — eat, grow, don't crash! | Arrows/WASD |
| 2 | Block Stack — Tetris-style falling blocks | Arrows move, Up rotate, Space hard-drop |
| 3 | 2048 — slide and merge to 2048 | Arrows/WASD, R restart |
| 4 | Minesweeper — clear mines without boom | Arrows + Space dig, F flag |
| 5 | Tic-Tac-Toe vs computer (unbeatable-ish minimax) | Arrows + Space, or 1-9 |
| 6 | Hangman — guess the secret word (2,800+ words) | Type letters |
| 7 | Pong vs CPU — first to 5 | Up/Down or W/S |
| 8 | Invaders — shoot the descending aliens | Left/Right or A/D, Space |
| 9 | Breakout — smash every brick, 3 lives | Left/Right or A/D |
| 0 | Word Guess — 6 tries (1,000+ words) | Type + Enter, Backspace |
| a | Frogger — hop across the traffic! | Arrows/WASD hop |
| b | Simon — repeat the memory sequence | Watch, then press 1-4 |
| c | Sokoban — push boxes onto targets (205 rooms!) | Arrows/WASD push, R restart, U undo |
| f | Runner — run, jump, dodge, grab the exit! | Arrows/WASD move + jump, R room |
| d | Connect Four — line up four vs the CPU | Left/Right, Space/Enter or 1-7 |
| e | Flappy — flap through the pipes! | Space/Up flap |
| W | Bored Wondering — search the web, keyless | Type + Enter, Up/Down pick |
| H | High Scores — every best in raw + Bored Points | Up/Down scroll |
| T | Score Translator — raw number → BP for any game | Pick game, type number |
| ? | Help — how to play everything | Any key back |

Sokoban and Runner open a room picker: choose any unlocked room, or jump
straight into endless mode once you have cleared every built-in room.
Progress (highest room unlocked) is saved between sessions in
`~/.local/share/gamebored/progress.json`. After the last built-in room,
both games switch to seeded, procedurally generated rooms that go on
forever with slowly rising difficulty (`Generated level N` shows the
room number and seed).

Every game shows its controls on screen plus the universal keys (`p`
pause, `?` help, `q` menu), ends with a friendly game-over panel (score in
raw and BP, best, NEW HIGH SCORE, win/lose message), and returns to the
menu. High scores persist per game.

## Bored Points (BP)

Every game keeps its own raw score, translated into one universal unit:
Bored Points. Game-over panels show `Score: 248 -> 1,240 BP`, the High
Scores table (H) lists every best in raw and BP with a combined total, and
the Score Translator (T) converts any raw number for any game. Rates live in
`gamebored/translator.py`.

## Bored Wondering (W)

A search engine inside the app. Type a query and GameBored asks 3 free
sources that need no API key or signup — in parallel, with short timeouts:

1. **DuckDuckGo Instant Answer API** (`api.duckduckgo.com`)
2. **Wikipedia search API** (`en.wikipedia.org/w/api.php`)
3. **Hacker News Algolia API** (`hn.algolia.com/api/v1/search`)

Results merge, dedupe, and show in a scrollable list (title, source tag,
snippet, URL). `Enter` on a result shows the full summary plus the link.
Your recent queries are kept as history (Up recalls them). If a source
fails or you are offline, that source is skipped with a friendly note and
the rest still work — Wondering never crashes, and it is the only part of
GameBored that touches the network (the 2,853-word and 1,047-word lists in
`gamebored/data/` stay local and offline).

Text renders of the menu, Wondering, help, and every game live in
`docs/screenshots/` (regenerate with `python3 tools/capture.py`).

## Level credits

- Sokoban ships 205 built-in rooms: the 3 original GameBored tutorial
  rooms, a curated, solver-verified subset of **Microban by David W. Skinner**
  (155 puzzles, revised April 2000 — freely redistributable with credit,
  http://users.bentonrea.com/~sasquatch/sokoban/), and GameBored
  reverse-pulled extra rooms. Only the level layouts are borrowed; the
  parser, renderer, solver, progression, and endless generator are original.
- Runner's 60 rooms are original GameBored designs across six difficulty
  zones (pits, platforms, spikes, enemies, keys + locked doors, moving
  platforms).

Endless rooms in both games are generated on the fly (seeded): Sokoban by
reverse-pulling boxes from a solved state (solvable by construction, then
re-verified with the push-solver, regenerating on failure), Runner by
chaining platform hops within jump range (re-verified with the reachability
solver, regenerating on failure).

## Tests (developers)

Testing-only deps (never needed to play): `pip install -r requirements-test.txt`

```bash
python3 -m pytest tests/ -q
```

- `tests/test_logic.py` — unit tests for each game's rules (merges, minimax,
  feedback, collisions, win/lose paths) plus score-file handling.
- `tests/test_translator.py` — Bored Points rates, formatting, totals.
- `tests/test_words.py` — word-list loading, sizes, fallbacks (offline).
- `tests/test_smoke.py` — import + registry smoke checks.
- `tests/test_search.py` — mocked-network tests for search merge/dedupe and
  per-source error handling, a word-list-offline check, and one optional
  live test skipped when offline.
- `tests/test_v13.py` — v1.3.0: all 60 Runner rooms beatable, all 205
  Sokoban rooms solvable (time-boxed push-solver), sampled endless rooms
  solvable/beatable, progress save/load + endless unlock, translator rate.
- `tests/test_pty.py` — drives the real app headlessly in a pseudo-terminal
  (80x24): launches each of the 16 games from the menu (including through
  the Sokoban/Runner room pickers), sends gameplay input, quits back to
  the menu, and exits with status 0; also covers the translator, the new
  menu/help/Wondering/scores screens, level-select screens, pause +
  in-game help overlays, tiny-terminal and resize behavior.
