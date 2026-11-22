"""PARRY: the classic 1972 paranoid patient, after Colby.

Simulated anger / fear / mistrust levels shift with what you say, and a
bookies-and-mafia delusion storyline (horse racing, debts, being followed)
is revealed gradually as the talk goes on. Levels are drawn as small mood
bars in the same scrollable chat UI the ELIZA app uses. Only stdlib.
"""

import curses
import re
import time

from . import chatui as chatui_mod
from . import cpu as cpu_mod
from . import storage as storage_mod
from . import ui

TITLE = "Parry"
DESCRIPTION = "A troubled soul (1972 classic)"
CONTROLS = "Type + Enter | PgUp/PgDn scroll | help quit | q menu"
GAME_ID = "parry"
CATEGORY = "Talk"

SESSION_FILE = "parry_last.txt"

HELP_TEXT = (
    "This is PARRY, a 1972 classic: a suspicious patient who thinks "
    "bookies and the mafia are after him over horse-racing debts. "
    "Be kind and he may open up; threaten him and he shuts down. "
    "Watch his anger, fear, and mistrust bars. Type quit or bye to leave."
)

STORY_STAGES = [
    "I do not want to talk about why I am here.",
    "Let us just say I owe some money. People do not forget debts.",
    "It started at the track. The horses ... I had a system, you know.",
    "The bookies say I owe them. They send people to watch me.",
    "The mafia runs the betting. They know where I live now.",
    "They follow me. Even here, I can feel them watching through the walls.",
]

HOSTILE = ("hate", "stupid", "idiot", "dumb", "shut up", "loser",
           "kill you", "hurt you", "liar", "crazy", "nuts", "worthless")
THREAT = ("police", "cops", "arrest", "hospital", "locked", "kill",
          "hurt", "follow", "watching", "gun", "knife", "die", "dead")
KIND = ("friend", "trust", "help", "understand", "sorry", "care",
        "safe", "calm", "listen", "believe you", "on your side")
STORY_KEYS = ("bookie", "bookies", "mafia", "horse", "racing", "race",
              "track", "bet", "betting", "debt", "money", "owe",
              "gangster", "follow")

PARRY_QUESTIONS = [
    "Why do you ask that? Who sent you?",
    "What makes you ask me that, of all things?",
    "Are you writing this down for them?",
    "That is exactly what THEY would ask. Why?",
    "I do not have to answer that. Do I?",
]

DEFLECTIONS = [
    "I do not trust strangers who ask things like that.",
    "You would like to know, would you not?",
    "Why should I tell you anything?",
    "Everyone wants a piece of me. Even you.",
    "Let us talk about something else. Are you alone right now?",
    "Hm. I need to think about who you really are.",
]

WARM_OPENS = [
    "Maybe ... maybe you are all right. Go on.",
    "You sound decent. Not like the others. What else?",
    "All right. I will tell you a little. But this stays between us.",
    "Thank you for saying that. Nobody says that to me.",
]

ANGRY_SNAPS = [
    "Watch your mouth. I am not someone you push around.",
    "You sound just like them. Back off.",
    "Say that again and this conversation is over.",
    "I knew it. You are one of them, are you not?",
]

FEARFUL = [
    "Lower your voice. They could be listening right now.",
    "Do you see anyone behind you? Check. Please.",
    "I should not have said that. Forget I said that.",
    "My hands are shaking. Do you hear footsteps too?",
]

MISTRUSTFUL = [
    "How do I know you are not working for the bookies?",
    "That is what someone sent to pump me would say.",
    "Prove you are who you say you are. What is your name?",
    "I will answer when I decide I can trust you. Not before.",
]


def _clamp(value):
    try:
        return max(0, min(10, int(value)))
    except (TypeError, ValueError):
        return 0


def new_state():
    """Fresh PARRY mood state. Headless-testable."""
    return {"anger": 2, "fear": 3, "mistrust": 5, "turn": 0,
            "revealed": 0, "last_reply": "", "name": ""}


def _norm(text):
    text = (text or "").lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def mood_bars(state):
    """Small mood-bar strings for the header. Headless-testable."""
    out = []
    for key, label in (("anger", "Anger"), ("fear", "Fear"),
                       ("mistrust", "Mistrust")):
        level = _clamp(state.get(key, 0))
        out.append("%s [%s] %d/10" % (
            label, "#" * level + "-" * (10 - level), level))
    return out


def update_mood(state, text):
    """Shift anger/fear/mistrust from what the user said. Testable."""
    norm = " " + _norm(text) + " "
    for word in HOSTILE:
        if " " + word + " " in norm or word in norm.split(" "):
            state["anger"] = _clamp(state.get("anger", 0) + 2)
            state["mistrust"] = _clamp(state.get("mistrust", 0) + 1)
            break
    for word in THREAT:
        if word in norm:
            state["fear"] = _clamp(state.get("fear", 0) + 2)
            state["mistrust"] = _clamp(state.get("mistrust", 0) + 1)
            break
    for word in KIND:
        if word in norm:
            state["anger"] = _clamp(state.get("anger", 0) - 1)
            state["fear"] = _clamp(state.get("fear", 0) - 1)
            state["mistrust"] = _clamp(state.get("mistrust", 0) - 2)
            break
    if "?" in (text or ""):
        state["mistrust"] = _clamp(state.get("mistrust", 0) + 1)
    # Time heals slightly when the user is neutral.
    if not any(w in norm for w in HOSTILE + THREAT + KIND):
        state["anger"] = _clamp(state.get("anger", 0) - 1)
    return state


def _pick(state, options, salt=""):
    idx = (state.get("turn", 0) + len(salt)) % max(1, len(options))
    choice = options[idx % len(options)]
    if choice == state.get("last_reply") and len(options) > 1:
        choice = options[(idx + 1) % len(options)]
    return choice


def respond(state, text):
    """One PARRY reply; updates mood. Never sleeps. Headless-testable."""
    try:
        norm = _norm(text)
        if not norm:
            return "Say something. Silence means you are hiding something."
        state["turn"] = state.get("turn", 0) + 1
        update_mood(state, text)
        anger = _clamp(state.get("anger", 0))
        fear = _clamp(state.get("fear", 0))
        mistrust = _clamp(state.get("mistrust", 0))

        match = re.search(r"\bmy name is ([a-z][a-z\-']*)", norm)
        if match:
            state["name"] = match.group(1).title()[:40]
            answer = ("All right, %s. A name. Maybe you are real after all. "
                      "But I am still watching you." % state["name"])
            state["last_reply"] = answer
            return answer

        if any(k in norm for k in STORY_KEYS):
            stage = min(state.get("revealed", 0),
                        len(STORY_STAGES) - 1)
            detail = STORY_STAGES[stage]
            state["revealed"] = min(len(STORY_STAGES) - 1,
                                    state.get("revealed", 0) + 1)
            if mistrust >= 7:
                answer = ("So you know about that. Who told you? %s" % detail)
            elif anger >= 7:
                answer = ("Stay out of it, you hear me? %s" % detail)
            else:
                answer = ("%s Do not repeat that to anyone." % detail)
            state["last_reply"] = answer
            return answer

        if state.get("turn", 0) >= 4 and state.get("revealed", 0) < 2:
            state["revealed"] = 2
            answer = ("You keep asking. Fine ... " + STORY_STAGES[1] +
                      " Leave it at that.")
            state["last_reply"] = answer
            return answer

        if anger >= 7:
            answer = _pick(state, ANGRY_SNAPS, text)
        elif fear >= 7:
            answer = _pick(state, FEARFUL, text)
        elif mistrust >= 7:
            answer = _pick(state, MISTRUSTFUL, text)
        elif mistrust <= 3:
            answer = _pick(state, WARM_OPENS, text)
        elif norm.endswith("?") or "?" in (text or ""):
            answer = _pick(state, PARRY_QUESTIONS, text)
        else:
            answer = _pick(state, DEFLECTIONS, text)
        if answer == state.get("last_reply"):
            answer += " I mean it."
        state["last_reply"] = answer
        return answer
    except Exception:
        return "I do not trust this conversation one bit."


def opening_line():
    return ("Who are you? What do you want? ... Fine. Talk. "
            "But I am watching you.")


def think_seconds(state=None):
    difficulty = 0.0
    try:
        difficulty = min(1.0, (_clamp((state or {}).get("mistrust", 5)) / 10.0))
    except Exception:
        pass
    return cpu_mod.delay_seconds(difficulty=difficulty)


def save_transcript(transcript, path=None):
    try:
        path = path or storage_mod.data_path(SESSION_FILE)
        with open(path + ".tmp", "w", encoding="utf-8") as fh:
            for who, text in transcript or []:
                fh.write("%s: %s\n" % (who or "?", text))
        import os
        os.replace(path + ".tmp", path)
        return path
    except OSError:
        return path


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
    state = new_state()
    transcript = [("PARRY", opening_line())]
    editor = chatui_mod.InputState()
    scroll = 0
    from . import settings as settings_mod
    settings = settings_mod.load()
    while True:
        if ui.too_small(stdscr, 15, 50):
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
            stdscr, "PARRY  ·  a troubled soul (1972)",
            "Be gentle. He thinks the mafia is after him.",
            transcript, scroll, editor.buf,
            extra_header=tuple(mood_bars(state)))
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
        if editor.key(key) != "submit":
            continue
        text = editor.submit()
        if not text:
            continue
        low = text.strip().lower()
        if low in ("help", "?"):
            transcript.append(("YOU", text))
            transcript.append(("PARRY", HELP_TEXT))
            scroll = 0
            continue
        transcript.append(("YOU", text))
        scroll = 0
        if cpu_mod.think(stdscr, seconds=think_seconds(state),
                         label="PARRY is thinking") == "quit":
            save_transcript(transcript)
            return
        answer = respond(state, text)
        transcript.append(("PARRY", answer))
        if low in ("quit", "exit", "bye", "goodbye"):
            transcript.append(("PARRY", "Going? Good. Fewer eyes on me. "
                                        "Do not follow me."))
            save_transcript(transcript)
            chatui_mod.draw(stdscr, "PARRY  ·  a troubled soul (1972)",
                            "Goodbye.", transcript, 0, "",
                            extra_header=tuple(mood_bars(state)))
            try:
                stdscr.timeout(1200)
                stdscr.getch()
                stdscr.timeout(-1)
            except curses.error:
                pass
            return
