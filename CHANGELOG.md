# GameBored Changelog

## v1.5.0 — GameBored OS

The menu is now a tiny desktop, the computer opponents feel human, and
Bored Wondering reads you the whole story.

Desktop OS (`gamebored/app.py`, `gamebored/ui.py`):

- Top bar (`GameBored OS`, live clock, BP total), grid of ASCII app-icon
  tiles with names, bottom status bar with key hints; arrows move
  (up/down/left/right), `Enter` opens, `Esc`/`q` backs out.
- Groups: ACTION / PUZZLE / CLASSIC games, EXPLORE, new TOOLS
  (Notes/Calculator/Clock/Calendar/To-do) and SYSTEM (Settings/About).
- Short skippable boot splash (off in Settings or `GAMEBORED_NO_SPLASH=1`,
  skipped when stdout is not a tty so tests stay clean).
- `/` filters every app by name (the search launcher); last selection is
  remembered across launches via the existing `_menu_last` mechanism.
- Narrow terminals (< 70 cols) fall back to the classic list layout; tiny
  terminals still get the friendly "make the window bigger" screen;
  selection uses reverse video so monochrome terminals keep working.

New apps (all stdlib, offline, atomic saves under the data dir):

- Notes (`gamebored/notes.py`): create/list/open/edit/rename/delete with a
  confirm dialog; multi-line editor (arrows, backspace, enter, home/end)
  with autosave; notes are `.txt` files in `notes/`.
- Calculator (`gamebored/calc.py`): safe AST-based eval (no `eval()`),
  `+ - * / // % **` and parentheses, history in `calc.json`.
- Clock (`gamebored/clockapp.py`): wall clock, stopwatch, countdown timer
  with `1/2/3` modes, Space start/stop, beeps on finish.
- Calendar (`gamebored/calendarapp.py`): month grid, arrows move the day
  (across month borders), PgUp/PgDn change months, `t` jumps to today.
- To-do (`gamebored/todo.py`): add, check off, delete; `todos.json`.
- Settings (`gamebored/settings.py` + screen): color theme
  (default/midnight/forest/mono), CPU think pause on/off + speed
  (relaxed/normal/brisk), boot splash on/off; `settings.json`.
- About (`gamebored/sysinfo.py`): version, games/apps count, data-dir
  storage used, terminal info.

Human CPU opponents (`gamebored/cpu.py`): every computer opponent
(Tic-Tac-Toe, Connect Four, Pong) now pauses with an animated
`CPU is thinking...` indicator — 0.4–1.5s randomized, longer for tense
positions (endgame boards, winning/blocking replies), UI stays responsive
(`q`/`Esc` aborts instantly), Pong's paddle chases a stale noisy memory
of the ball with a dead zone instead of tracking perfectly. Configurable
in Settings; fully disabled via `GAMEBORED_NO_CPU_DELAY=1` for fast tests.

Bored Wondering reader (`gamebored/search.py`, `gamebored/wondering.py`):

- More results per source (up to 12) with long wrapped multi-line
  summaries; two new keyless sources (Wiktionary, Open Library).
- `Enter` opens a full-screen scrollable reader: complete Wikipedia
  article text (extracts API, section headings), HN story plus top
  comments (Algolia items API), full DDG abstract + infobox facts +
  related topics, Open Library descriptions/subjects.
- Source tabs (All/Wiki/DDG/HN/Dict/Books) on Left/Right, animated
  loading screen with cancel, friendly offline errors, recent-query cache
  (persisted `wonder_cache.json`, "cached" badge), `n` opens the next
  result, `/` finds text inside the reader.

Also: `install.sh`/`uninstall.sh` now preserve notes, to-dos, calculator
history, the search cache, and settings (not just scores/progress);
`--list` shows games + apps; version 1.5.0 (`__init__.py`, search
`USER_AGENT`, README, screenshots).

Full suite: 200+ passing (`python3 -m pytest tests -q`), including 47 new
`tests/test_v15.py` tests, plus a manual `install.sh`/`uninstall.sh`
round-trip verified with a scratch HOME, and `python3 -m gamebored --list`
showing 16 games + 11 apps.

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

- Round 40: Sokoban gains undo (`u`, 2000-step history, cleared on
  restart) so one wrong push no longer ruins a room.
- Round 41: Sokoban tracks fewest moves per room in `progress.json`
  (`get_best`/`record_best`) and shows `best:N` in the HUD.
- Round 42: the menu remembers the last picked game across sessions
  (`_menu_last` in the scores store).
- Round 43: menu `/` filter with a status line and empty-state handling.
- Round 44: Runner `r` restarts the room keeping score and lives.
- Round 45: every game's CONTROLS line advertises `? help` (8 fixed).
- Round 46: Sokoban picker shows `(best N)` per cleared room.
- Round 47: Runner flashes `OUCH! N lives left` for a second on a
  non-final death.
- Round 48: fixed the pty menu test (fresh HOME; remembered selection
  had scrolled the asserted entry out of view).
- Round 49: the `?` help overlay documents `/ filter`.
- Round 50: High Scores shows per-game play counts.
- Round 51: README documents undo/room-restart/filter; screenshots
  regenerated for sixteen games.
- Round 52: removed dead `ui.FOOTER_HELP`; Wondering CONTROLS says
  `q/Esc menu`.
- Round 53: the pause overlay headline names the game
  (`PAUSED - <title>`), passed as TITLE by all sixteen games.
- Round 54: Sokoban and Runner room pickers answer `?` with the help
  overlay like every other screen.
- Round 55: Sokoban footer says `boxes home N/M` instead of cryptic
  `home N/M`.

- Round 56: Runner CONTROLS and README say `r restart room` instead
  of cryptic `r room`.
- Round 57: Sokoban and Runner room-picker footers advertise `? help`
  (they answer it since Round 54).
- Round 58: the full Help screen documents `/ filter`.
- Round 59: Runner flashes `CLEAR! +bonus` (from ROOM_BONUS) for 1.2s on
  room clear, mirroring the OUCH! death toast.
- Round 60: Sokoban flashes `SOLVED!` for 1.2s on room clear (level and
  endless modes), mirroring Runner.

- Round 61: Runner footer says `score N`, not `room score N` — the
  score persists across rooms.
- Round 62: guard test proves all sixteen games call
  `pause_overlay(stdscr, TITLE)` so the pause screen always names the game.
- Round 63: `uninstall.sh` backs up `progress.json` and `install.sh`
  restores it — reinstalling no longer wipes unlocked rooms or bests.

Final: version stays 1.4.0, full suite green (150 passed), a manual
`install.sh`/`uninstall.sh` round-trip verified with a scratch HOME, and
`python3 -m gamebored --list` shows 16 games including Runner.

## v1.2.0 — polished menu, Bored Wondering search, pause/help everywhere
## v1.1.0 — fifteen games, bigger word lists, Bored Points Score Translator
## v1.0.0 — colorful curses arcade with 10 games, installer, tests
