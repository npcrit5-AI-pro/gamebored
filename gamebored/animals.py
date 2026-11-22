"""ANIMALS: the classic learning guessing game.

Think of an animal, answer yes/no, and the program guesses. When it is
wrong it asks for your animal plus a distinguishing yes/no question, learns
it, and remembers forever (atomic save in the data dir). Ships with a seed
tree of 40 animals. Only the standard library is used.
"""

import curses

from . import chatui as chatui_mod
from . import storage as storage_mod
from . import ui

TITLE = "Animals"
DESCRIPTION = "Think of an animal, I guess it"
CONTROLS = "y/n answers | q menu"
GAME_ID = "animals"
CATEGORY = "Talk"

FILE_NAME = "animals_tree.json"


def Q(question, yes, no):  # noqa: N802 - tiny tree DSL
    return {"question": question, "yes": yes, "no": no}


def A(name):  # noqa: N802 - tiny tree DSL
    return {"animal": name}


def seed_tree():
    """The built-in tree: 40 animals. Headless-testable."""
    aquatic = Q("Does it have fins and gills?",
                Q("Is it a big hunter with sharp teeth?",
                  A("shark"),
                  Q("Does it live in a school and get eaten by bears?",
                    A("salmon"),
                    A("goldfish"))),
                Q("Is it a huge mammal that spouts water?",
                  Q("Does it have black-and-white coloring and waddle?",
                    A("penguin"),
                    Q("Does it sing songs in the ocean?",
                      A("whale"),
                      A("dolphin"))),
                  Q("Does it have eight arms?",
                    A("octopus"),
                    Q("Does it walk sideways with claws?",
                      A("crab"),
                      A("seal")))))
    flyers = Q("Is it a bird?",
               Q("Does it hoot at night?",
                 A("owl"),
                 Q("Can it copy human speech?",
                   A("parrot"),
                   Q("Is it a large bird of prey?",
                     A("eagle"),
                     Q("Does it lay eggs you eat for breakfast?",
                       A("chicken"),
                       A("duck"))))),
               Q("Does it crawl with no legs?",
                 A("snake"),
                 Q("Does it have eight legs?",
                   A("spider"),
                   Q("Does it buzz and make honey?",
                     A("bee"),
                     Q("Does it flutter with colorful wings?",
                       A("butterfly"),
                       Q("Is it small, hopping, and green near ponds?",
                         A("frog"),
                         A("lizard")))))))
    pets = Q("Does it bark?",
             A("dog"),
             Q("Does it purr?",
               A("cat"),
               Q("Does it hop with long ears?",
                 Q("Is it tiny with a twitchy nose?",
                   A("mouse"),
                   A("rabbit")),
                 Q("Does it climb trees and hoard nuts?",
                   A("squirrel"),
                   Q("Is it sly with a bushy tail?",
                     A("fox"),
                     A("wolf"))))))
    farm = Q("Do people ride it?",
             Q("Does it have a long neck and spots?",
               A("giraffe"),
               A("horse")),
             Q("Does it give milk?",
               Q("Is it woolly and says baa?",
                 A("sheep"),
                 A("cow")),
               Q("Does it roll in mud and oink?",
                 A("pig"),
                 Q("Does it have antlers?",
                   A("deer"),
                   Q("Does it butt heads on mountains?",
                     A("goat"),
                     A("donkey"))))))
    wild = Q("Is it a big cat?",
             Q("Does it have a mane?",
               A("lion"),
               Q("Does it have orange stripes?",
                 A("tiger"),
                 A("leopard"))),
             Q("Does it love bamboo?",
               A("panda"),
               Q("Does it hibernate in winter?",
                 A("bear"),
                 Q("Does it hop with a pouch?",
                   A("kangaroo"),
                   Q("Is it armored and rolls into a ball?",
                     A("armadillo"),
                     A("crocodile"))))))
    return Q("Does it live mostly in water?",
             aquatic,
             Q("Can it fly or glide through the air?",
               flyers,
               Q("Does it live with people as a pet or pest?",
                 pets,
                 Q("Is it a farm animal?",
                   farm,
                   wild))))


def _clean_tree(node):
    if isinstance(node, dict):
        if isinstance(node.get("animal"), str) and node["animal"].strip():
            return {"animal": node["animal"].strip()[:60]}
        question = node.get("question")
        yes, no = node.get("yes"), node.get("no")
        if isinstance(question, str) and question.strip():
            clean_yes, clean_no = _clean_tree(yes), _clean_tree(no)
            if clean_yes is not None and clean_no is not None:
                return {"question": question.strip()[:160],
                        "yes": clean_yes, "no": clean_no}
    return None


def load_tree(path=None):
    raw = storage_mod.load_json(
        FILE_NAME, None, path=path or storage_mod.data_path(FILE_NAME))
    clean = _clean_tree(raw)
    if clean is None:
        return seed_tree()
    return clean


def save_tree(tree, path=None):
    storage_mod.save_json(
        FILE_NAME, tree, path=path or storage_mod.data_path(FILE_NAME))
    return tree


def count_animals(tree):
    """How many animals the tree knows. Headless-testable."""
    if not isinstance(tree, dict):
        return 0
    if isinstance(tree.get("animal"), str):
        return 1
    return count_animals(tree.get("yes")) + count_animals(tree.get("no"))


def list_animals(tree):
    """Sorted animal names. Headless-testable."""
    if not isinstance(tree, dict):
        return []
    if isinstance(tree.get("animal"), str):
        return [tree["animal"]]
    return sorted(list_animals(tree.get("yes")) + list_animals(tree.get("no")))


def ask_path(tree, answers):
    """Follow yes/no answers; returns (node, exhausted_ok). Testable."""
    node = tree
    for answer in answers or []:
        if not isinstance(node, dict) or "question" not in node:
            return node, False
        node = node.get("yes" if answer else "no")
    return node, True


def learn(tree, answers, new_animal, question, answer_for_new):
    """Replace the reached leaf with a distinguishing question. Testable.

    answers: path of booleans to the wrongly-guessed leaf. Returns the
    (possibly new root) tree.
    """
    new_animal = (new_animal or "").strip()[:60]
    question = (question or "").strip()
    if not question.endswith("?"):
        question = question + "?"
    if not new_animal or len(question) < 4:
        return tree
    node = tree
    parent = None
    parent_key = None
    for answer in answers or []:
        if not isinstance(node, dict) or "question" not in node:
            return tree
        parent, parent_key = node, ("yes" if answer else "no")
        node = node.get(parent_key)
    if not isinstance(node, dict) or not node.get("animal"):
        return tree
    old_animal = node["animal"]
    if old_animal.lower() == new_animal.lower():
        return tree
    if answer_for_new:
        fixed = Q(question, A(new_animal), A(old_animal))
    else:
        fixed = Q(question, A(old_animal), A(new_animal))
    if parent is None:
        return fixed
    parent[parent_key] = fixed
    return tree


YES_WORDS = ("y", "yes", "yeah", "yep", "sure", "true", "1")
NO_WORDS = ("n", "no", "nope", "nah", "false", "0")


def parse_yes_no(text):
    """True/False/None for yes/no/undecided. Headless-testable."""
    norm = (text or "").strip().lower()
    if norm in YES_WORDS:
        return True
    if norm in NO_WORDS:
        return False
    return None


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
    tree = load_tree()
    save_tree(tree)
    transcript = [(None, "Think of an animal. I will guess it with "
                         "yes/no questions. I know %d animals so far."
                 % count_animals(tree))]
    node = tree
    answers = []
    editor = chatui_mod.InputState()
    scroll = 0
    mode = "asking"  # asking -> guess -> new_animal -> new_q -> new_a
    pending = {}
    while True:
        if ui.too_small(stdscr, 14, 50):
            ui.show_too_small(stdscr)
            try:
                key = stdscr.getch()
            except curses.error:
                key = -1
            if key in ui.QUIT_KEYS:
                save_tree(tree)
                return
            continue
        if mode == "asking":
            prompt = node.get("question", "Is it ...?") + "  (y/n)"
        elif mode == "guess":
            prompt = "Is it a %s?  (y/n)" % node.get("animal", "?")
        elif mode == "new_animal":
            prompt = "I give up! What animal were you thinking of?"
        elif mode == "new_q":
            prompt = ("Give a yes/no question that is TRUE for %s "
                      "but FALSE for %s:" % (pending.get("new"),
                                             pending.get("old")))
        else:
            prompt = ("For %s, is the answer yes or no?  (y/n)"
                      % pending.get("new"))
        header = ("ANIMALS  ·  I know %d animals  ·  %s"
                  % (count_animals(tree), prompt))
        scroll = chatui_mod.draw(
            stdscr, header, "Answer y/n. q leaves (progress is kept).",
            transcript, scroll, editor.buf)
        try:
            key = stdscr.getch()
        except curses.error:
            key = -1
        if key in ui.QUIT_KEYS and not editor.buf:
            save_tree(tree)
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
        transcript.append(("YOU", text))
        if mode in ("asking", "guess", "new_a"):
            verdict = parse_yes_no(text)
            if verdict is None:
                transcript.append((None, "Please answer y or n."))
                scroll = 0
                continue
        if mode == "asking":
            answers.append(bool(verdict))
            transcript.append((None, node["question"] + "  -> %s" %
                               ("yes" if verdict else "no")))
            node = node.get("yes" if verdict else "no")
            if isinstance(node, dict) and "question" in node:
                pass
            else:
                mode = "guess"
        elif mode == "guess":
            if verdict:
                transcript.append((None, "Got it! I knew it was a %s. "
                                        "Think of another one!" %
                                   node.get("animal")))
                node, answers, mode = tree, [], "asking"
            else:
                pending = {"old": node.get("animal", "thing"),
                           "answers": list(answers)}
                transcript.append((None, "Rats! I do not know it yet."))
                mode = "new_animal"
        elif mode == "new_animal":
            if len(text.strip()) < 2:
                transcript.append((None, "Tell me the animal in a word or two."))
            else:
                pending["new"] = text.strip()[:60]
                mode = "new_q"
        elif mode == "new_q":
            if len(text.strip()) < 4:
                transcript.append((None, "Give me a real question, ending "
                                        "with ? ideally."))
            else:
                pending["question"] = text.strip()[:160]
                mode = "new_a"
        elif mode == "new_a":
            tree = learn(tree, pending.get("answers", []),
                         pending.get("new"), pending.get("question"),
                         bool(verdict))
            save_tree(tree)
            transcript.append((None, "Learned! Now I know %d animals. "
                                    "Think of another one!" %
                               count_animals(tree)))
            node, answers, pending, mode = tree, [], {}, "asking"
        scroll = 0
