"""v1.6.0 tests: Talk group (Eliza, Parry, Animals, versus).

All headless (no network, no curses init). CPU delays are forced off via
GAMEBORED_NO_CPU_DELAY so the suite stays fast.
"""

import os
import sys
import time

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["GAMEBORED_NO_SPLASH"] = "1"
os.environ["GAMEBORED_NO_CPU_DELAY"] = "1"

from gamebored import animals as animals_mod  # noqa: E402
from gamebored import app as app_mod  # noqa: E402
from gamebored import chatui as chatui_mod  # noqa: E402
from gamebored import cpu as cpu_mod  # noqa: E402
from gamebored import eliza as eliza_mod  # noqa: E402
from gamebored import eliza_script as script_mod  # noqa: E402
from gamebored import parry as parry_mod  # noqa: E402
from gamebored import versus as versus_mod  # noqa: E402


def fresh_eliza(tmp_path):
    return eliza_mod.new_session(path=str(tmp_path / "eliza.json"))


# --- script size -----------------------------------------------------------


class TestScriptSize:
    def test_keyword_count(self):
        assert script_mod.keyword_count() >= 90

    def test_reassembly_count(self):
        assert script_mod.reassembly_count() >= 400

    def test_synonym_groups(self):
        syns = script_mod.SYNONYMS
        assert "family" in syns and len(syns["family"]) >= 2
        assert "belief" in syns

    def test_xnone_fallbacks(self):
        assert len(script_mod.XNONE) >= 10

    def test_ranks_span(self):
        ranks = [e.get("rank", 0) for e in script_mod.KEYWORDS]
        assert max(ranks) >= 8
        assert min(ranks) <= 0

    def test_keywords_unique(self):
        words = [e.get("word") for e in script_mod.KEYWORDS]
        assert len(words) == len(set(words))

    def test_every_keyword_has_rules(self):
        for entry in script_mod.KEYWORDS:
            assert entry.get("rules"), entry.get("word")
            for decomp, options in entry["rules"]:
                assert isinstance(decomp, str) and decomp.strip()
                assert len(options) >= 2, entry.get("word")


# --- reflection ------------------------------------------------------------


class TestReflection:
    def test_pronoun_swap(self):
        assert eliza_mod.reflect("i love my mother") == "you love your mother"

    def test_you_to_i(self):
        assert eliza_mod.reflect("you hate me") == "I hate you"

    def test_verb_swap(self):
        assert eliza_mod.reflect("i am sad") == "you are sad"
        assert eliza_mod.reflect("you were happy") == "I was happy"

    def test_mine_yours(self):
        assert "yours" in eliza_mod.reflect("that is mine")
        assert "mine" in eliza_mod.reflect("that is yours")


# --- rank selection --------------------------------------------------------


class TestRankSelection:
    def test_specific_beats_generic(self):
        entry = eliza_mod.choose_keyword("i think my mother hates me")
        assert entry is not None and entry["word"] == "mother"

    def test_sorry_beats_i(self):
        entry = eliza_mod.choose_keyword("i am sorry you are here")
        assert entry is not None and entry["word"] == "sorry"

    def test_why_beats_generic(self):
        entry = eliza_mod.choose_keyword("why do you say i am tired")
        assert entry is not None and entry["word"] == "why"

    def test_reply_uses_top_keyword_real(self, tmp_path):
        state = fresh_eliza(tmp_path)
        answer = eliza_mod.reply(state, "i think my mother hates me")
        assert "mother" in answer.lower()


# --- memory -----------------------------------------------------------------


class TestMemory:
    def test_name_fact_recall(self, tmp_path):
        state = fresh_eliza(tmp_path)
        eliza_mod.reply(state, "my name is Fred")
        assert state["mem"]["name"] == "Fred"
        answer = eliza_mod.reply(state, "what is my name?")
        assert "Fred" in answer

    def test_name_persists_across_sessions(self, tmp_path):
        path = str(tmp_path / "eliza.json")
        first = eliza_mod.new_session(path=path)
        eliza_mod.reply(first, "my name is Fred")
        eliza_mod.save_memory(first["mem"], path=path)
        second = eliza_mod.new_session(path=path)
        assert "Fred" in eliza_mod.opening_line(second)

    def test_likes_recall(self, tmp_path):
        state = fresh_eliza(tmp_path)
        eliza_mod.reply(state, "i love chess")
        assert "chess" in state["mem"]["likes"]
        answer = eliza_mod.reply(state, "what do i like?")
        assert "chess" in answer.lower()

    def test_my_statement_memory_stack(self, tmp_path):
        state = fresh_eliza(tmp_path)
        eliza_mod.reply(state, "my dog is sick")
        answer = eliza_mod.reply(state, "zqxwv blib blob")
        assert "dog" in answer.lower()

    def test_topic_recall(self, tmp_path):
        state = fresh_eliza(tmp_path)
        eliza_mod.reply(state, "i work at a bank and feel stuck")
        assert "work" in state["mem"]["topics"]
        seen = [eliza_mod.reply(state, "quux blorple wug %d" % i)
                for i in range(3)]
        assert any("work" in a.lower() for a in seen)


# --- no immediate repeats ----------------------------------------------------


class TestNoRepeats:
    def test_same_input_never_repeats(self, tmp_path):
        state = fresh_eliza(tmp_path)
        answers = [eliza_mod.reply(state, "tell me about life") for _ in range(10)]
        assert all(a != b for a, b in zip(answers, answers[1:]))

    def test_fallbacks_cycle(self, tmp_path):
        state = fresh_eliza(tmp_path)
        answers = [eliza_mod.reply(state, "quux blorple wug %d" % i)
                   for i in range(12)]
        assert all(a != b for a, b in zip(answers, answers[1:]))
        assert len(set(answers)) > 3


# --- PARRY moods -------------------------------------------------------------


class TestParryMoods:
    def test_hostile_raises_anger(self):
        state = parry_mod.new_state()
        before = (state["anger"], state["mistrust"])
        parry_mod.update_mood(state, "you are stupid and I hate you")
        assert state["anger"] > before[0]
        assert state["mistrust"] >= before[1]

    def test_kindness_lowers_mistrust(self):
        state = parry_mod.new_state()
        parry_mod.update_mood(state, "I am your friend, I want to help")
        assert state["mistrust"] < 5
        assert state["anger"] <= 2

    def test_threats_raise_fear(self):
        state = parry_mod.new_state()
        parry_mod.update_mood(state, "the police are watching and will arrest you")
        assert state["fear"] > 3

    def test_mood_stays_in_range(self):
        state = parry_mod.new_state()
        for _ in range(20):
            parry_mod.update_mood(state, "stupid hate kill police liar")
        for key in ("anger", "fear", "mistrust"):
            assert 0 <= state[key] <= 10

    def test_storyline_revealed_gradually(self):
        state = parry_mod.new_state()
        first = parry_mod.respond(state, "do the bookies work for the mafia?")
        assert state["revealed"] >= 1
        joined = first
        for _ in range(4):
            joined += " " + parry_mod.respond(state, "tell me about the horses")
        low = joined.lower()
        assert any(word in low for word in ("bookie", "mafia", "horse",
                                            "track", "debt", "follow"))

    def test_mood_bars_format(self):
        bars = parry_mod.mood_bars(parry_mod.new_state())
        assert len(bars) == 3
        assert all("[" in b and "]" in b for b in bars)
        assert bars[0].startswith("Anger")

    def test_parry_never_sleeps(self):
        state = parry_mod.new_state()
        start = time.time()
        for i in range(20):
            parry_mod.respond(state, "what do you think about %d?" % i)
        assert time.time() - start < 5


# --- Animals ------------------------------------------------------------------


class TestAnimals:
    def test_seed_tree_size(self):
        tree = animals_mod.seed_tree()
        assert animals_mod.count_animals(tree) >= 40

    def test_list_matches_count(self):
        tree = animals_mod.seed_tree()
        assert len(animals_mod.list_animals(tree)) == \
            animals_mod.count_animals(tree)

    def test_learning_grows_tree(self):
        tree = animals_mod.seed_tree()
        before = animals_mod.count_animals(tree)
        node, _ = animals_mod.ask_path(tree, [True, True, True])
        # walk to a leaf deterministically
        answers = []
        cursor = tree
        while isinstance(cursor, dict) and "question" in cursor:
            answers.append(True)
            cursor = cursor["yes"]
        assert isinstance(cursor, dict) and cursor.get("animal")
        tree = animals_mod.learn(tree, answers, "wombat",
                                 "Does it carry babies in a backward pouch?",
                                 True)
        assert animals_mod.count_animals(tree) == before + 1
        assert "wombat" in animals_mod.list_animals(tree)

    def test_learn_distinguishes(self):
        tree = animals_mod.seed_tree()
        answers = []
        cursor = tree
        while isinstance(cursor, dict) and "question" in cursor:
            answers.append(False)
            cursor = cursor["no"]
        old = cursor["animal"]
        tree = animals_mod.learn(tree, answers, "unicorn",
                                 "Does it have a horn?", True)
        node, _ = animals_mod.ask_path(tree, answers)
        assert node["question"] == "Does it have a horn?"
        assert node["yes"]["animal"] == "unicorn"
        assert node["no"]["animal"] == old

    def test_persistence_roundtrip(self, tmp_path):
        path = str(tmp_path / "animals.json")
        tree = animals_mod.load_tree(path=path)
        answers = []
        cursor = tree
        while isinstance(cursor, dict) and "question" in cursor:
            answers.append(True)
            cursor = cursor["yes"]
        tree = animals_mod.learn(tree, answers, "wombat",
                                 "Does it waddle?", False)
        animals_mod.save_tree(tree, path=path)
        reloaded = animals_mod.load_tree(path=path)
        assert animals_mod.count_animals(reloaded) == \
            animals_mod.count_animals(tree)
        assert "wombat" in animals_mod.list_animals(reloaded)

    def test_parse_yes_no(self):
        assert animals_mod.parse_yes_no("yes") is True
        assert animals_mod.parse_yes_no("N") is False
        assert animals_mod.parse_yes_no("maybe") is None
        assert animals_mod.parse_yes_no("") is None


# --- versus --------------------------------------------------------------------


class TestVersus:
    def test_exchange_alternates(self, tmp_path):
        convo = versus_mod.run_exchange(
            4, seed="I feel watched.",
            eliza_path=str(tmp_path / "eliza.json"))
        assert len(convo) == 8
        speakers = [who for who, _text in convo]
        assert speakers == ["ELIZA", "PARRY"] * 4
        assert all(isinstance(t, str) and t.strip() for _w, t in convo)

    def test_exchange_is_fast(self, tmp_path):
        start = time.time()
        versus_mod.run_exchange(6, eliza_path=str(tmp_path / "e.json"))
        assert time.time() - start < 10


# --- chat UI helpers ------------------------------------------------------------


class TestChatUI:
    def test_wrap_and_flatten(self):
        lines = chatui_mod.flatten([("YOU", "hello there"),
                                    ("ELIZA", "hi back")], 40)
        assert lines[0].startswith("YOU:")
        assert any(l.startswith("ELIZA:") for l in lines)

    def test_visible_lines_pins_bottom(self):
        all_lines = ["l%d" % i for i in range(20)]
        assert chatui_mod.visible_lines(all_lines, 5, 0) == all_lines[-5:]
        assert chatui_mod.visible_lines(all_lines, 5, 2) == all_lines[-7:-2]

    def test_input_history(self):
        editor = chatui_mod.InputState()
        for ch in "hello":
            editor.key(ord(ch))
        assert editor.key(10) == "submit"
        assert editor.submit() == "hello"
        editor.key(ord("x"))
        editor.key(curses_key_up())
        assert editor.buf == "hello"

    def test_think_delay_disabled_in_tests(self, tmp_path):
        state = fresh_eliza(tmp_path)
        eliza_mod.reply(state, "hello")
        assert eliza_mod.think_seconds(state) == 0.0
        assert cpu_mod.delay_seconds(difficulty=1.0) == 0.0


def curses_key_up():
    import curses
    return curses.KEY_UP


# --- desktop + install -------------------------------------------------------------


class TestDesktop:
    def test_talk_entries_present(self):
        entries = app_mod.build_entries()
        talk = [e for e in entries if e.get("category") == "TALK"]
        assert len(talk) == 4
        hotkeys = sorted(e["hotkey"] for e in talk)
        assert hotkeys == ["J", "K", "U", "V"]
        titles = sorted(e["title"] for e in talk)
        assert titles == ["Animals", "Eliza", "Eliza vs Parry", "Parry"]

    def test_talk_hotkeys_unique(self):
        entries = app_mod.build_entries()
        keys = [e.get("hotkey", "").lower() for e in entries if e.get("hotkey")]
        assert len(keys) == len(set(keys))

    def test_talk_hotkeys_reachable(self):
        entries = app_mod.build_entries()
        for hot in ("J", "K", "U", "V"):
            assert app_mod.hotkey_index(entries, ord(hot.lower())) is not None

    def test_list_mentions_talk(self, capsys):
        from gamebored import __main__ as main_mod
        assert main_mod.main(["--list"]) == 0
        out = capsys.readouterr().out
        for word in ("Eliza", "Parry", "Animals"):
            assert word in out

    def test_install_preserves_talk_data(self):
        repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        for name in ("install.sh", "uninstall.sh"):
            with open(os.path.join(repo, name), encoding="utf-8") as fh:
                text = fh.read()
            assert "eliza_memory.json" in text, name
            assert "animals_tree.json" in text, name
