"""ELIZA: a faithful Weizenbaum DOCTOR-style therapist, upgraded.

Classic mechanics: keywords with ranks, decomposition/reassembly rules,
pronoun reflection (I->you, my->your, ...), synonym groups, a memory stack
for ``my`` statements, cycling reassemblies, ``xnone`` fallbacks.

Upgrades: remembers facts you tell it (name, likes, family members) within
and across sessions (persisted in the data dir), refers back to earlier
topics, handles greetings/goodbyes/questions, never repeats the same reply
twice in a row, pauses like a person (``cpu.py`` think delay), scrollable
transcript, session save, and ``help``. The script itself lives in
``eliza_script.py`` so it is easy to extend. Only stdlib is used.
"""

import curses
import os
import re
import time

from . import chatui as chatui_mod
from . import cpu as cpu_mod
from . import eliza_script as script_mod
from . import storage as storage_mod
from . import ui

TITLE = "Eliza"
DESCRIPTION = "A caring (mechanical) listener"
CONTROLS = "Type + Enter | PgUp/PgDn scroll | help save quit | q menu"
GAME_ID = "eliza"
CATEGORY = "Talk"

FILE_NAME = "eliza_memory.json"
SESSION_FILE = "eliza_last.txt"

HELP_TEXT = (
    "I am ELIZA, a classic listening program. Just talk to me. "
    "Commands: help (this), save (keep our chat), quit or bye (leave). "
    "I remember your name, likes, and family between visits. "
    "PgUp/PgDn scrolls our conversation."
)

REFLECT = {
    "i": "you", "me": "you", "my": "your", "mine": "yours",
    "myself": "yourself", "you": "I", "your": "my", "yours": "mine",
    "yourself": "myself", "am": "are", "are": "am",
    "was": "were", "were": "was",
    "i'm": "you're", "you're": "I'm", "i've": "you've",
    "you've": "I've", "i'll": "you'll", "you'll": "I'll",
    "i'd": "you'd", "you'd": "I'd", "us": "you",
}

GREETING_WORDS = ("hello", "hi", "hey", "howdy", "greetings",
                  "good morning", "good afternoon", "good evening")
GOODBYE_WORDS = ("goodbye", "bye", "farewell", "quit", "exit",
                 "goodnight", "good night", "see you", "gtg", "cya")

MEMORY_TEMPLATES = [
    "Earlier you said %s. Tell me more about that.",
    "Does that have anything to do with the fact that %s?",
    "You mentioned %s before. How does that connect?",
]

TOPIC_TEMPLATE = ("Earlier you mentioned %s. Can you say more about it?")


def _clean_word(word):
    return re.sub(r"[^a-z0-9'\-]", "", (word or "").lower())


def normalize(text):
    """Lowercase, punctuation to spaces, single-spaced. Headless-testable."""
    text = (text or "").lower()
    text = re.sub(r"[^a-z0-9'\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def reflect(text):
    """Swap pronouns point-of-view. Headless-testable."""
    out = []
    for word in (text or "").split():
        key = _clean_word(word)
        out.append(REFLECT.get(key, word))
    result = " ".join(out)
    result = re.sub(r"\bi ([a-z])", r"I \1", result)
    return result


def _expand_synonyms(text):
    words = normalize(text).split()
    alias_to_canon = {}
    for canon, aliases in (script_mod.SYNONYMS or {}).items():
        for alias in aliases or []:
            alias_to_canon[normalize(alias)] = normalize(canon)
    return " ".join(alias_to_canon.get(w, w) for w in words)


def _word_positions(text):
    words = normalize(text).split()
    pos = {}
    for i, word in enumerate(words):
        pos.setdefault(_clean_word(word), i)
    canon = _expand_synonyms(text).split()
    for i, word in enumerate(canon):
        pos.setdefault(_clean_word(word), i)
    return pos


def choose_keyword(text):
    """Highest-rank keyword present in text (ties: earliest). Testable."""
    pos = _word_positions(text)
    best, best_key = None, None
    for order, entry in enumerate(script_mod.KEYWORDS or []):
        word = _clean_word(entry.get("word", ""))
        if not word or word not in pos:
            continue
        key = (-int(entry.get("rank", 0) or 0), pos[word], order)
        if best_key is None or key < best_key:
            best, best_key = entry, key
    return best


def _decomp_to_regex(decomp):
    pieces = []
    for tok in (decomp or "").lower().split():
        if tok.strip() == "*":
            pieces.append(("cap", None))
        else:
            cleaned = re.sub(r"[^a-z0-9'\-]", "", tok)
            if cleaned:
                pieces.append(("lit", cleaned))
    regex = r"^\s*"
    for i, (kind, val) in enumerate(pieces):
        if kind == "cap":
            regex += "(.*?)"
        else:
            regex += re.escape(val)
        if i < len(pieces) - 1:
            nxt = pieces[i + 1][0]
            regex += r"\s*" if (kind == "cap" or nxt == "cap") else r"\s+"
    regex += r"\s*$"
    return regex


def _match_decomp(decomp, text):
    try:
        match = re.match(_decomp_to_regex(decomp), normalize(text))
    except re.error:
        return None
    if not match:
        return None
    return [reflect((g or "").strip()) for g in match.groups()]


def _fill(reassembly, groups):
    def _sub(match):
        try:
            idx = int(match.group(1)) - 1
        except (TypeError, ValueError):
            return match.group(0)
        if 0 <= idx < len(groups):
            return groups[idx]
        return ""
    return re.sub(r"\((\d+)\)", _sub, reassembly or "")


def _default_memory():
    return {"name": "", "likes": [], "dislikes": [],
            "family": {}, "topics": [], "visits": 0}


def load_memory(path=None):
    raw = storage_mod.load_json(
        FILE_NAME, {}, path=path or storage_mod.data_path(FILE_NAME))
    mem = _default_memory()
    if not isinstance(raw, dict):
        return mem
    if isinstance(raw.get("name"), str):
        mem["name"] = raw["name"].strip()[:40]
    for key in ("likes", "dislikes", "topics"):
        vals = raw.get(key)
        if isinstance(vals, list):
            mem[key] = [v for v in vals if isinstance(v, str)][:40]
    fam = raw.get("family")
    if isinstance(fam, dict):
        for key, val in fam.items():
            if isinstance(key, str) and isinstance(val, str):
                mem["family"][key[:20]] = val[:60]
    try:
        mem["visits"] = max(0, int(raw.get("visits", 0)))
    except (TypeError, ValueError):
        mem["visits"] = 0
    return mem


def save_memory(mem, path=None):
    try:
        clean = _default_memory()
        clean.update({k: v for k, v in (mem or {}).items() if k in clean})
        storage_mod.save_json(
            FILE_NAME, clean, path=path or storage_mod.data_path(FILE_NAME))
    except Exception:
        pass
    return mem


def new_session(path=None):
    """Fresh runtime state bound to persisted memory. Headless-testable."""
    mem = load_memory(path=path)
    mem["visits"] = mem.get("visits", 0) + 1
    state = {"mem": mem, "path": path, "turn": 0,
             "counters": {}, "last_reply": "",
             "mem_stack": [], "xnone_idx": 0, "ended": False}
    save_memory(mem, path=path)
    return state


def opening_line(state):
    mem = state.get("mem", {})
    name = (mem.get("name") or "").strip()
    if mem.get("visits", 1) > 1 and name:
        return ("Welcome back, %s. I remembered you. "
                "What is on your mind today?" % name)
    if mem.get("visits", 1) > 1:
        return ("Welcome back. I kept what you told me safe. "
                "What shall we talk about?")
    return ("Hello. I am ELIZA, your terminal therapist. "
            "Type help any time. What is on your mind?")


def _remember_facts(state, text, original):
    mem = state["mem"]
    norm = normalize(text)
    changed = False
    match = re.search(r"\bmy name is ([a-z][a-z\-']*(?: [a-z][a-z\-']*){0,2})",
                      norm)
    if match:
        mem["name"] = match.group(1).strip().title()[:40]
        changed = True
    else:
        match = re.search(r"\bcall me ([a-z][a-z\-']*(?: [a-z][a-z\-']*){0,2})",
                          norm)
        if match:
            mem["name"] = match.group(1).strip().title()[:40]
            changed = True
    match = re.search(
        r"\bi (?:like|love|enjoy|adore) ([a-z][a-z'\- ]{1,40})", norm)
    if match:
        thing = re.sub(r"\s+", " ", match.group(1)).strip()[:40]
        thing = re.sub(r"\s+(very much|a lot|so much)$", "", thing).strip()
        if thing and thing not in (mem.get("likes") or []):
            mem.setdefault("likes", []).append(thing)
            mem["likes"] = mem["likes"][-20:]
            changed = True
    match = re.search(
        r"\bi (?:dislike|hate|can'?t stand) ([a-z][a-z'\- ]{1,40})", norm)
    if match:
        thing = re.sub(r"\s+", " ", match.group(1)).strip()[:40]
        if thing and thing not in (mem.get("dislikes") or []):
            mem.setdefault("dislikes", []).append(thing)
            mem["dislikes"] = mem["dislikes"][-20:]
            changed = True
    match = re.search(
        r"\bmy (mother|father|mom|dad|sister|brother|wife|husband|son|"
        r"daughter|friend|boyfriend|girlfriend) (?:is|is named|is called|"
        r"names? ) ([a-z][a-z\-']*(?: [a-z][a-z\-']*){0,2})", norm)
    if match:
        mem.setdefault("family", {})[match.group(1)] = (
            match.group(2).strip().title()[:60])
        changed = True
    if changed:
        save_memory(mem, path=state.get("path"))
    return changed


def _push_memory(state, text):
    norm = normalize(text)
    if " my " not in (" " + norm + " "):
        return
    try:
        frag = norm.split("my ", 1)[1]
    except IndexError:
        return
    frag = re.sub(r"\s+", " ", frag).strip()
    frag = " ".join(frag.split()[:9])
    if len(frag) < 2:
        return
    reflected = "your " + " ".join(
        REFLECT.get(_clean_word(w), w) for w in frag.split()[0:8])
    stack = state.setdefault("mem_stack", [])
    if reflected not in stack:
        stack.append(reflected)
    del stack[:-8]


def _recall_name(state, norm):
    name = (state.get("mem", {}).get("name") or "").strip()
    if not name:
        return None
    if (("your name" in norm or "my name" in norm or
            "who am i" in norm or "remember me" in norm) and
            ("what" in norm or "remember" in norm or "who" in norm or
             "?" in norm)):
        return ("You told me your name is %s, and I kept it safe. "
                "How are you feeling today, %s?" % (name, name))
    return None


def _recall_likes(state, norm):
    likes = state.get("mem", {}).get("likes") or []
    if not likes:
        return None
    if ("like" in norm and
            ("what" in norm or "remember" in norm or "do i" in norm)):
        if len(likes) == 1:
            return ("You told me you like %s. Tell me more about that."
                    % likes[-1])
        return ("You told me you like %s, among other things. "
                "Which matters most right now?"
                % ", ".join(likes[-3:]))
    return None


def _next_reassembly(state, word, rule_idx, options):
    key = "%s:%d" % (word, rule_idx)
    idx = state["counters"].get(key, 0)
    for _ in range(len(options) + 1):
        candidate = options[idx % len(options)]
        idx += 1
        if candidate != state.get("last_reply"):
            break
    state["counters"][key] = idx
    return candidate


def reply(state, text):
    """One ELIZA reply. Never raises; never sleeps. Headless-testable."""
    try:
        original = (text or "")
        norm = normalize(original)
        if not norm:
            return "I am listening. Please, tell me something."
        state["turn"] = state.get("turn", 0) + 1
        mem = state["mem"]
        _remember_facts(state, original, original)

        recalled = _recall_name(state, norm)
        if recalled:
            state["last_reply"] = recalled
            return recalled
        recalled = _recall_likes(state, norm)
        if recalled:
            state["last_reply"] = recalled
            return recalled

        entry = choose_keyword(" " + norm + " ")
        if entry is not None and int(entry.get("rank", 0) or 0) > 0:
            word = entry["word"]
            topics = mem.setdefault("topics", [])
            if word not in topics:
                topics.append(word)
                mem["topics"] = topics[-20:]
                save_memory(mem, path=state.get("path"))
            rules = entry.get("rules", [])
            start = state["counters"].get("rule:%s" % word, 0)
            for offset in range(len(rules)):
                rule_idx = (start + offset) % max(1, len(rules))
                decomp, options = rules[rule_idx]
                groups = _match_decomp(decomp, norm)
                if groups is None or not options:
                    continue
                state["counters"]["rule:%s" % word] = rule_idx + 1
                candidate = _next_reassembly(state, word, rule_idx, options)
                answer = _fill(candidate, groups)
                answer = re.sub(r"\s+", " ", answer).strip()
                if not answer:
                    continue
                state["last_reply"] = answer
                _push_memory(state, norm)
                return answer

        _push_memory(state, norm)
        stack = state.get("mem_stack", [])
        if stack:
            frag = stack.pop(0)
            template = MEMORY_TEMPLATES[
                state.get("turn", 1) % len(MEMORY_TEMPLATES)]
            answer = template % frag
            if answer == state.get("last_reply") and stack:
                frag = stack.pop(0)
                answer = template % frag
            state["last_reply"] = answer
            return answer

        topics = mem.get("topics") or []
        idx = state.get("xnone_idx", 0)
        state["xnone_idx"] = idx + 1
        if topics and idx % 3 == 2:
            answer = TOPIC_TEMPLATE % topics[idx % len(topics)]
            if answer != state.get("last_reply"):
                state["last_reply"] = answer
                return answer
        options = script_mod.XNONE
        candidate = options[idx % len(options)]
        if candidate == state.get("last_reply"):
            candidate = options[(idx + 1) % len(options)]
            state["xnone_idx"] = idx + 2
        state["last_reply"] = candidate
        return candidate
    except Exception:
        return "Please go on. I am listening."


def think_seconds(state=None, settings=None):
    """Human-feeling pause length; 0 when disabled (fast tests)."""
    difficulty = 0.0
    try:
        if state and state.get("last_reply"):
            difficulty = min(1.0, len(state["last_reply"]) / 240.0)
    except Exception:
        pass
    return cpu_mod.delay_seconds(difficulty=difficulty, settings=settings)


def save_transcript(transcript, path=None, stamp=None):
    """Persist a chat transcript; returns the file path. Never raises."""
    try:
        if path is None:
            name = SESSION_FILE if not stamp else "eliza_session_%s.txt" % stamp
            path = storage_mod.data_path(name)
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(path + ".tmp", "w", encoding="utf-8") as fh:
            for who, text in transcript or []:
                fh.write("%s: %s\n" % (who or "?", text))
        os.replace(path + ".tmp", path)
        return path
    except OSError:
        return path


def _is_goodbye(norm):
    padded = " " + (norm or "") + " "
    for g in GOODBYE_WORDS:
        if " " + g + " " in padded:
            return True
    return (norm or "").strip() in ("quit", "exit", "bye", "cya", "gtg")


def play(stdscr, _score_store=None):
    try:
        curses.curs_set(0)
    except curses.error:
        pass
    try:
        stdscr.keypad(True)
        stdscr.timeout(-1)
    except curses.error:
        pass
    state = new_session()
    transcript = [("ELIZA", opening_line(state))]
    editor = chatui_mod.InputState()
    scroll = 0
    status = ""
    from . import settings as settings_mod
    settings = settings_mod.load()
    while True:
        if ui.too_small(stdscr, 14, 50):
            ui.show_too_small(stdscr)
            try:
                key = stdscr.getch()
            except curses.error:
                key = -1
            if key in ui.QUIT_KEYS:
                save_transcript(transcript)
                return
            continue
        scroll = chatui_mod.draw(
            stdscr, "ELIZA  ·  terminal therapist", status or HELP_TEXT,
            transcript, scroll, editor.buf)
        if status:
            status = ""
        try:
            key = stdscr.getch()
        except curses.error:
            key = -1
        if key in ui.QUIT_KEYS and not editor.buf:
            save_transcript(transcript)
            return
        if key == curses.KEY_PPAGE:
            scroll += 5
            continue
        if key == curses.KEY_NPAGE:
            scroll = max(0, scroll - 5)
            continue
        if key == curses.KEY_RESIZE:
            continue
        result = editor.key(key)
        if result != "submit":
            continue
        text = editor.submit()
        if not text:
            continue
        low = text.strip().lower()
        if low in ("help", "?"):
            transcript.append(("YOU", text))
            transcript.append(("ELIZA", HELP_TEXT))
            scroll = 0
            continue
        if low in ("save", "save chat"):
            transcript.append(("YOU", text))
            stamp = time.strftime("%Y%m%d-%H%M%S")
            path = save_transcript(transcript, stamp=stamp)
            save_transcript(transcript)
            transcript.append(
                ("ELIZA", "I saved our conversation (%s). Go on." %
                 os.path.basename(path or "chat")))
            scroll = 0
            continue
        transcript.append(("YOU", text))
        scroll = 0
        if cpu_mod.think(stdscr, seconds=think_seconds(state, settings),
                         label="ELIZA is thinking") == "quit":
            save_transcript(transcript)
            return
        answer = reply(state, text)
        transcript.append(("ELIZA", answer))
        if _is_goodbye(normalize(text)):
            state["ended"] = True
            save_transcript(transcript)
            chatui_mod.draw(stdscr, "ELIZA  ·  terminal therapist",
                            "Goodbye.", transcript, 0, "")
            try:
                stdscr.timeout(1200)
                stdscr.getch()
                stdscr.timeout(-1)
            except curses.error:
                pass
            return
