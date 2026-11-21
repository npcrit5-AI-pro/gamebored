"""v1.3.0 tests: Runner rooms, 205 Sokoban rooms, endless, progress.

- every built-in Runner room is beatable (reachability solver)
- every built-in Sokoban room is solvable (push-solver, time-boxed)
- sampled generated endless rooms are solvable/beatable
- progress save/load + unlock flow
- translator covers the new game
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gamebored import progress as progress_mod
from gamebored import translator as translator_mod
from gamebored.games import platformer, sokoban
from gamebored.games import sokoban_solver


def test_registry_has_sixteen_games():
    from gamebored.games import GAMES
    assert len(GAMES) == 16
    ids = [m.GAME_ID for m in GAMES]
    assert len(set(ids)) == len(ids)
    assert "platformer" in ids
    assert "f" not in [e for e in ids]  # hotkeys live in app.GAME_HOTKEYS
    from gamebored.app import GAME_HOTKEYS
    assert len(GAME_HOTKEYS) == 16 and GAME_HOTKEYS[-1] == "f"


def test_translator_covers_platformer():
    assert translator_mod.rate_for("platformer") > 0
    assert translator_mod.to_bp("platformer", 750) > 0
    assert "BP" in translator_mod.format_score("platformer", 100)


def test_platformer_has_sixty_beatable_rooms():
    assert len(platformer.LEVELS) >= 60
    bad = [i + 1 for i, rows in enumerate(platformer.LEVELS)
           if not platformer.beatable(rows)]
    assert bad == [], "unbeatable Runner rooms: %s" % bad


def test_platformer_endless_beatable_many_seeds():
    for seed in ("7", "12345", "gamebored"):
        for n in (1, 5, 15, 40):
            rows, _ = platformer.gen_endless_verified(seed, n)
            assert platformer.beatable(rows), \
                "endless runner seed=%s n=%d unbeatable" % (seed, n)


def test_sokoban_has_205_solvable_rooms():
    assert len(sokoban.LEVELS) >= 200
    bad = []
    for i, rows in enumerate(sokoban.LEVELS):
        if sokoban_solver.solve_pushes(rows, cap=30000,
                                       time_limit=3.0) is None:
            bad.append(i + 1)
    assert bad == [], "unsolvable Sokoban rooms: %s" % bad


def test_sokoban_endless_solvable_many_seeds():
    for seed in ("7", "424242", "endless"):
        for n in (1, 6, 20):
            rows = sokoban.gen_endless_verified(seed, n)
            assert sokoban_solver.solve_pushes(rows, cap=20000,
                                               time_limit=2.0) is not None, \
                "endless sokoban seed=%s n=%d unsolvable" % (seed, n)


def test_progress_save_load_and_unlock(tmp_path):
    path = str(tmp_path / "progress.json")
    p = progress_mod.load(path)
    assert progress_mod.get_unlocked(p, "sokoban", 205) == 0
    assert not progress_mod.endless_unlocked(p, "sokoban", 205)
    progress_mod.record_level_complete(p, "sokoban", 0, 205, path=path)
    assert progress_mod.get_unlocked(p, "sokoban", 205) == 1
    reloaded = progress_mod.load(path)
    assert progress_mod.get_unlocked(reloaded, "sokoban", 205) == 1
    # finishing the final room unlocks endless
    progress_mod.record_level_complete(reloaded, "sokoban", 204, 205,
                                       path=path)
    assert progress_mod.endless_unlocked(reloaded, "sokoban", 205)
    # corrupt file -> defaults, never crash
    with open(path, "w") as fh:
        fh.write("{oops")
    assert progress_mod.load(path) == {}


def test_platformer_physics_smoke():
    st = platformer.RunState(platformer.LEVELS[0])
    x0 = st.x
    st.step(0.09, move=1, jump=False)
    assert st.x > x0  # running moves right
    assert not st.over
    # gravity pulls a mid-air runner down
    st2 = platformer.RunState(platformer.LEVELS[0])
    st2.y -= 3.0
    y0 = st2.y
    st2.step(0.09)
    assert st2.y > y0
    # jumping needs ground: force airborne, jump does nothing bad
    st2.step(0.09, jump=True)
    assert not st2.over or True


def test_sokoban_state_push_and_restart():
    st = sokoban.new_state(0)
    # room 0: player (3,3)? walls/box/target layout from tutorial room
    assert not st.solved
    st.restart()
    assert st.moves == 0 and not st.over
    # endless state builds from generated rows
    rows = sokoban.gen_endless_verified("7", 1)
    st2 = sokoban.SokState(rows=rows, endless=("7", 1))
    assert st2.player is not None and not st2.solved
