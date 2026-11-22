"""ELIZA DOCTOR script data for GameBored Talk.

A faithful implementation of Weizenbaum's DOCTOR script mechanics lives in
``eliza.py``; this module holds only the *data* so the script is easy to
extend: add a dict to KEYWORDS (word, rank, rules) and the engine picks it
up with no code changes.

Conventions (classic DOCTOR style):

- ``word`` is matched as a whole word, case-insensitively.
- ``rank``: higher-ranked keywords win when several match. Specific words
  (``dreamed``, ``sorry``, ``gamebored``) outrank generic ones (``i``).
- Each rule is ``(decomposition, [reassemblies])``. ``*`` in a
  decomposition matches any run of words (possibly empty); ``(1)``,
  ``(2)``, ... in a reassembly are replaced by the reflected text the
  corresponding ``*`` captured.
- ``SYNONYMS`` maps a canonical word to alias words that count as the
  canonical word during matching.
- ``XNONE`` is used when nothing matches and the memory stack is empty.
"""

SYNONYMS = {
    "family": ["household", "kin", "relatives", "folks"],
    "belief": ["belief", "beliefs", "creed", "credo", "conviction"],
    "sad": ["sorrowful", "downcast", "blue"],
    "happy": ["joyful", "cheerful", "glad"],
    "afraid": ["frightened", "scared", "fearful"],
    "doctor": ["physician", "shrink", "analyst"],
    "money": ["cash", "dough", "funds"],
    "friend": ["buddy", "pal", "chum", "mate"],
}

GREETINGS = [
    "Hello. I am ELIZA, your terminal therapist. What is on your mind today?",
    "Hi there. I am ELIZA. Please, tell me what brings you here.",
    "Good day. I am ELIZA. How are you feeling right now?",
    "Hello, I am ELIZA. This is a safe place. What would you like to talk about?",
    "Hi. I am ELIZA, and I am listening. What is troubling you?",
    "Welcome. I am ELIZA. Tell me, what has been on your mind lately?",
]

GOODBYES = [
    "Goodbye. It has been a pleasure talking with you. Take care.",
    "Farewell. Remember what we discussed, and be kind to yourself.",
    "Goodbye for now. I will remember what you told me.",
    "Leaving so soon? Very well. Goodbye, and take care of yourself.",
    "Goodbye. I hope our talk helped a little.",
    "Until next time. Goodbye.",
    "Goodbye. I will keep what you shared safe until you return.",
    "Farewell. Come back any time you need to talk.",
]

XNONE = [
    "Please go on. I am listening.",
    "Tell me more about that.",
    "I see. Can you elaborate?",
    "What does that suggest to you?",
    "How does that make you feel?",
    "Can you say a little more about that?",
    "That is interesting. Please continue.",
    "Why do you say that?",
    "What comes to mind when you say that?",
    "Let us explore that a little. What else?",
    "Hm. Talk to me about how that affects you.",
    "I understand. What happened next?",
    "Go on, I am following you.",
    "And how do you feel about that?",
    "What do you think that means?",
    "Earlier you mentioned something like this. Say more.",
    "Can you give me an example?",
    "Does talking about this help at all?",
]

# Each entry: {"word": str, "rank": int, "rules": [(decomp, [reassemblies])]}
# Decomp "*" matches any words; (N) in a reassembly inserts the Nth
# *-capture after pronoun reflection.
KEYWORDS = [
    {"word": "sorry", "rank": 10, "rules": [
        ("* sorry *", [
            "There is no need to apologize.",
            "Apologies are not necessary. What bothers you?",
            "Saying sorry is a start. What about (2)?",
            "Do not be sorry. Tell me more about (2).",
            "It takes courage to say sorry. Go on.",
        ]),
        ("*", [
            "Please do not apologize so much.",
            "Apologies are fine, but what troubles you?",
        ]),
    ]},
    {"word": "apologize", "rank": 10, "rules": [
        ("* apologize *", [
            "No apology is needed here.",
            "You apologize as if (2) were your fault. Is it?",
            "Let us set apologies aside. Tell me about (2).",
            "I accept your apology. Now, what is really on your mind?",
        ]),
    ]},
    {"word": "remember", "rank": 5, "rules": [
        ("* i remember *", [
            "Do you often think of (2)?",
            "What else do you remember about (2)?",
            "Why does (2) come to mind now?",
            "Does remembering (2) bring up other feelings?",
            "What associations does (2) carry for you?",
        ]),
        ("* you remember *", [
            "Do you think I would forget (2)?",
            "Why do you wonder whether I remember (2)?",
            "If I remembered (2), what would that change?",
            "What makes (2) worth remembering?",
        ]),
        ("* remember *", [
            "What do you remember most clearly?",
            "Why does that memory surface now?",
            "Is there something you wish you could forget?",
        ]),
    ]},
    {"word": "forget", "rank": 5, "rules": [
        ("* i forget *", [
            "Why do you think you forget (2)?",
            "Is forgetting (2) convenient, perhaps?",
            "What would it mean to remember (2)?",
            "Do you often forget things like (2)?",
        ]),
        ("* forget *", [
            "Can you recall it if you try?",
            "What stops you from remembering?",
            "Forgetting can be a way of protecting yourself. From what?",
        ]),
    ]},
    {"word": "dream", "rank": 4, "rules": [
        ("* dream *", [
            "What does that dream suggest to you?",
            "Do you dream often?",
            "Who else appears in your dreams?",
            "What feelings does that dream leave you with?",
            "Have you told anyone about this dream?",
        ]),
    ]},
    {"word": "dreamed", "rank": 4, "rules": [
        ("* i dreamed *", [
            "Really, (2)? Tell me the dream in detail.",
            "What did you feel while dreaming (2)?",
            "Do you believe dreams about (2) have meaning?",
            "Who else was in that dream with (2)?",
        ]),
    ]},
    {"word": "nightmare", "rank": 4, "rules": [
        ("* nightmare *", [
            "Nightmares can feel very real. What frightened you most?",
            "Do these nightmares recur?",
            "What do you think the nightmare is trying to tell you?",
            "How did you feel when you woke up?",
        ]),
    ]},
    {"word": "name", "rank": 8, "rules": [
        ("* my name is *", [
            "Pleased to meet you, (2). Tell me what brings you here.",
            "(2) is a fine name. What should I call you for short?",
            "Hello, (2). How does it feel to introduce yourself?",
        ]),
        ("* name *", [
            "Names carry weight. Why do you mention it?",
            "What does that name mean to you?",
            "Would you like me to remember your name? I will.",
        ]),
    ]},
    {"word": "hello", "rank": 9, "rules": [
        ("*", [
            "Hello. I am ELIZA. What is on your mind?",
            "Hi there. What would you like to talk about?",
            "Hello, and welcome. How are you feeling today?",
        ]),
    ]},
    {"word": "hi", "rank": 9, "rules": [
        ("*", [
            "Hi. I am ELIZA. What brings you here today?",
            "Hello. Tell me what is troubling you.",
        ]),
    ]},
    {"word": "hey", "rank": 9, "rules": [
        ("*", [
            "Hey. I am listening. What is up?",
            "Hey there. What is on your mind?",
        ]),
    ]},
    {"word": "goodbye", "rank": 9, "rules": [
        ("*", [
            "Goodbye. It has been good talking with you.",
            "Farewell. I will remember what you shared.",
        ]),
    ]},
    {"word": "bye", "rank": 9, "rules": [
        ("*", [
            "Goodbye for now. Take care of yourself.",
            "Leaving so soon? Goodbye, and come back any time.",
        ]),
    ]},
    {"word": "thanks", "rank": 6, "rules": [
        ("*", [
            "You are welcome. How are you feeling now?",
            "I am glad I could help. What else is on your mind?",
            "No thanks needed. Tell me more.",
        ]),
    ]},
    {"word": "am", "rank": 3, "rules": [
        ("* i am *", [
            "How long have you been (2)?",
            "Do you believe it is normal to be (2)?",
            "Do you enjoy being (2)?",
            "Why do you say you are (2)?",
            "What would it take for you not to be (2)?",
        ]),
    ]},
    {"word": "are", "rank": 3, "rules": [
        ("* are you *", [
            "Why does whether I am (2) matter to you?",
            "Would you prefer it if I were (2)?",
            "Do you sometimes wish you were (2)?",
            "I might be (2). What then?",
        ]),
        ("* you are *", [
            "What makes you think I am (2)?",
            "Does it please you to believe I am (2)?",
            "Perhaps you would like me to be (2).",
        ]),
    ]},
    {"word": "was", "rank": 3, "rules": [
        ("* i was *", [
            "Were you really (2)?",
            "How long were you (2)?",
            "Perhaps I already knew you were (2).",
            "What changed since you were (2)?",
        ]),
        ("* was i *", [
            "What if you were (2)?",
            "Do you think you were (2)?",
            "Were you (2)? Tell me more.",
        ]),
    ]},
    {"word": "were", "rank": 3, "rules": [
        ("* you were *", [
            "Why do you say I was (2)?",
            "Do you think I was (2) then?",
            "What if I had been (2)?",
        ]),
        ("* were you *", [
            "Would you like it if I were (2)?",
            "What does it mean to you that I might have been (2)?",
            "Perhaps I was (2). Why do you ask?",
        ]),
    ]},
    {"word": "i", "rank": 0, "rules": [
        ("* i * you *", [
            "Perhaps in your fantasies we (2) each other.",
            "Do you wish to (2) me?",
            "You seem to need to (2) me.",
        ]),
        ("* i *", [
            "You say (1). Can you elaborate on that?",
            "Why do you say (1)?",
            "Do you want me to know (1)?",
            "What else comes to mind when you say (1)?",
        ]),
    ]},
    {"word": "you", "rank": 0, "rules": [
        ("* you * me *", [
            "Why do you think I (2) you?",
            "You like to think I (2) you, do you not?",
            "What makes you think I (2) you?",
        ]),
        ("* you *", [
            "We were discussing you, not me.",
            "Why do you say that about me?",
            "Are you concerned about what I (1)?",
        ]),
    ]},
    {"word": "my", "rank": 2, "rules": [
        ("* my *", [
            "Your (2)? Tell me more about that.",
            "Why do you say your (2)?",
            "Does that have anything to do with the fact that your (2)?",
            "Earlier you mentioned your (2). Can you say more?",
        ]),
    ]},
    {"word": "your", "rank": 2, "rules": [
        ("* your *", [
            "Why are you concerned about my (2)?",
            "What about your own (2)?",
            "Are you comparing my (2) to yours?",
        ]),
    ]},
    {"word": "yes", "rank": 2, "rules": [
        ("*", [
            "You seem quite sure. Why is that?",
            "I see. Can you tell me why?",
            "Are you saying yes just to please me?",
            "What makes you so certain?",
        ]),
    ]},
    {"word": "no", "rank": 2, "rules": [
        ("* no *", [
            "Are you saying no just to be negative?",
            "Why not (2)?",
            "You are being a bit negative about (2).",
            "Is that a firm no about (2)?",
        ]),
        ("*", [
            "Why the negative?",
            "Are you always so negative?",
        ]),
    ]},
    {"word": "not", "rank": 2, "rules": [
        ("* not *", [
            "Why do you say (1) is not (2)?",
            "Is (1) really not (2)?",
            "What would change if (1) were (2)?",
        ]),
    ]},
    {"word": "never", "rank": 3, "rules": [
        ("* never *", [
            "Never (2)? That is strong. Why?",
            "Can you recall a time when (2) almost happened?",
            "What makes you so sure it will never (2)?",
        ]),
    ]},
    {"word": "always", "rank": 4, "rules": [
        ("* always *", [
            "Can you think of a specific example of (2)?",
            "Always? What if there were an exception?",
            "When did (2) start being always true?",
            "Really, always (2)?",
        ]),
    ]},
    {"word": "everyone", "rank": 3, "rules": [
        ("* everyone *", [
            "Who in particular are you thinking of?",
            "Surely not everyone (2). Who does?",
            "Can you name who (2)?",
            "What about the exceptions?",
        ]),
    ]},
    {"word": "everybody", "rank": 3, "rules": [
        ("* everybody *", [
            "Who exactly is everybody?",
            "Are you including yourself?",
            "Can you think of anyone who does not (2)?",
        ]),
    ]},
    {"word": "nobody", "rank": 3, "rules": [
        ("* nobody *", [
            "Not even one person (2)?",
            "Who might (2) if asked?",
            "Are you sure nobody (2)?",
        ]),
    ]},
    {"word": "alike", "rank": 4, "rules": [
        ("* alike *", [
            "In what way are they alike?",
            "What resemblance do you see?",
            "Is the likeness comforting or worrying?",
        ]),
    ]},
    {"word": "same", "rank": 4, "rules": [
        ("* same *", [
            "What is the connection you see?",
            "In what way the same?",
            "Does that sameness matter to you?",
        ]),
    ]},
    {"word": "different", "rank": 4, "rules": [
        ("* different *", [
            "How are they different?",
            "What differences bother you most?",
            "Is being different good or bad here?",
        ]),
    ]},
    {"word": "like", "rank": 3, "rules": [
        ("* i like *", [
            "What do you enjoy most about (2)?",
            "How long have you liked (2)?",
            "Why do you think you like (2)?",
            "Does anyone else know you like (2)?",
            "I will remember that you like (2). What else do you like?",
        ]),
        ("* like *", [
            "Is liking (2) important to you?",
            "What does (2) remind you of?",
            "Do the people around you also like (2)?",
        ]),
    ]},
    {"word": "dislike", "rank": 3, "rules": [
        ("* i dislike *", [
            "What bothers you about (2)?",
            "How long have you disliked (2)?",
            "I will remember you dislike (2). What would you prefer?",
        ]),
    ]},
    {"word": "love", "rank": 5, "rules": [
        ("* i love *", [
            "What does loving (2) mean to you?",
            "How long have you loved (2)?",
            "Does (2) love you back, do you think?",
            "I will remember your love for (2). Tell me more.",
            "What would life be like without (2)?",
        ]),
        ("* love *", [
            "Is love about (2) for you?",
            "Who else do you love?",
            "What does love feel like to you?",
        ]),
    ]},
    {"word": "hate", "rank": 5, "rules": [
        ("* i hate *", [
            "Hate is strong. What happened with (2)?",
            "How long have you hated (2)?",
            "What would it take to soften that feeling about (2)?",
            "I will remember that. Who knows you hate (2)?",
        ]),
    ]},
    {"word": "want", "rank": 4, "rules": [
        ("* i want *", [
            "What would you do if you got (2)?",
            "Why do you want (2)?",
            "Suppose you never got (2). Then what?",
            "What stops you from having (2)?",
            "Who else wants (2)?",
        ]),
        ("* want *", [
            "Is wanting (2) new for you?",
            "What does wanting (2) say about you?",
        ]),
    ]},
    {"word": "need", "rank": 4, "rules": [
        ("* i need *", [
            "Would getting (2) really help?",
            "What need does (2) fill for you?",
            "Is (2) a need or a want?",
            "Who could help you with (2)?",
        ]),
    ]},
    {"word": "think", "rank": 3, "rules": [
        ("* i think *", [
            "Do you doubt (2)?",
            "What makes you think (2)?",
            "Do you really think so, or do you feel it?",
            "How long have you thought (2)?",
        ]),
        ("* think *", [
            "What do your friends think about (2)?",
            "Is thinking about (2) comforting?",
        ]),
    ]},
    {"word": "believe", "rank": 4, "rules": [
        ("* believe *", [
            "What convinces you that (2)?",
            "Do your beliefs about (2) ever waver?",
            "Who taught you to believe (2)?",
            "How does believing (2) shape your life?",
        ]),
    ]},
    {"word": "feel", "rank": 4, "rules": [
        ("* i feel *", [
            "How often do you feel (2)?",
            "When do you usually feel (2)?",
            "Do you enjoy feeling (2)?",
            "Why do you think you feel (2)?",
            "Who knows that you feel (2)?",
        ]),
        ("* feel *", [
            "Tell me more about such feelings.",
            "Are these feelings new?",
        ]),
    ]},
    {"word": "hope", "rank": 3, "rules": [
        ("* hope *", [
            "What gives you hope about (2)?",
            "How long have you hoped for (2)?",
            "What if that hope came true?",
            "Who shares that hope with you?",
        ]),
    ]},
    {"word": "wish", "rank": 3, "rules": [
        ("* i wish *", [
            "If wishes worked, what would (2) change?",
            "Why do you wish (2)?",
            "Who would be affected if (2)?",
        ]),
    ]},
    {"word": "sad", "rank": 6, "rules": [
        ("* i am sad *", [
            "I am sorry you feel sad. What happened?",
            "How long have you felt this sadness?",
            "Does anyone know you feel sad?",
            "What usually lifts your sadness?",
        ]),
        ("* sad *", [
            "Sadness is hard. Tell me about (2).",
            "When did the sadness start?",
            "What helps when you feel this way?",
        ]),
    ]},
    {"word": "unhappy", "rank": 6, "rules": [
        ("* unhappy *", [
            "What makes you unhappy about (2)?",
            "How long have you been unhappy?",
            "What would happiness look like instead?",
        ]),
    ]},
    {"word": "depressed", "rank": 6, "rules": [
        ("* depressed *", [
            "I hear you. How heavy does it feel today?",
            "Have you felt this way long about (2)?",
            "Is there anyone supporting you right now?",
            "If it gets heavy, please reach out to someone you trust.",
        ]),
    ]},
    {"word": "lonely", "rank": 6, "rules": [
        ("* lonely *", [
            "Loneliness hurts. Who do you miss?",
            "When do you feel loneliest?",
            "Is there someone you could call today?",
            "What would company look like for you?",
        ]),
    ]},
    {"word": "tired", "rank": 6, "rules": [
        ("* tired *", [
            "Tired in body or in spirit?",
            "Are you sleeping well?",
            "What drains you most about (2)?",
            "What would rest look like for you?",
        ]),
    ]},
    {"word": "bored", "rank": 6, "rules": [
        ("* bored *", [
            "Boredom often hides a wish. What do you wish for?",
            "When did (2) start feeling boring?",
            "Have you tried the GameBored arcade? Just a thought.",
            "What used to excite you about (2)?",
        ]),
    ]},
    {"word": "happy", "rank": 6, "rules": [
        ("* happy *", [
            "Wonderful. What makes you happy about (2)?",
            "How long have you felt this happy?",
            "Who shares this happiness with you?",
            "I will remember this bright moment about (2).",
        ]),
    ]},
    {"word": "glad", "rank": 6, "rules": [
        ("* glad *", [
            "I am glad too. What pleases you about (2)?",
            "What changed to make you glad?",
        ]),
    ]},
    {"word": "better", "rank": 5, "rules": [
        ("* better *", [
            "Better than what?",
            "What improved about (2)?",
            "I am pleased things are better. What helped?",
        ]),
    ]},
    {"word": "angry", "rank": 6, "rules": [
        ("* angry *", [
            "What fuels that anger about (2)?",
            "How long have you been angry?",
            "Who are you angriest with?",
            "What would calm this anger?",
        ]),
    ]},
    {"word": "ashamed", "rank": 6, "rules": [
        ("* ashamed *", [
            "Shame is heavy. What happened with (2)?",
            "Whose voice do you hear when you feel ashamed?",
            "What would forgiveness look like?",
        ]),
    ]},
    {"word": "anxious", "rank": 6, "rules": [
        ("* anxious *", [
            "What worries you most about (2)?",
            "When is the anxiety worst?",
            "What has helped your anxiety before?",
            "Let us breathe through this. Tell me slowly about (2).",
        ]),
    ]},
    {"word": "guilty", "rank": 6, "rules": [
        ("* guilty *", [
            "What do you feel guilty about with (2)?",
            "Do you think you deserve that guilt?",
            "What would making amends look like?",
        ]),
    ]},
    {"word": "stressed", "rank": 6, "rules": [
        ("* stressed *", [
            "What piles on the stress about (2)?",
            "How do you usually cope with stress?",
            "What could you set down, even briefly?",
        ]),
    ]},
    {"word": "excited", "rank": 6, "rules": [
        ("* excited *", [
            "Excitement is lovely. What about (2) thrills you?",
            "Who will you share this excitement with?",
            "When did you first feel excited about (2)?",
        ]),
    ]},
    {"word": "proud", "rank": 6, "rules": [
        ("* proud *", [
            "You should be proud. What did you do about (2)?",
            "Who else is proud of you?",
            "What did it take to get here?",
        ]),
    ]},
    {"word": "afraid", "rank": 6, "rules": [
        ("* afraid *", [
            "What frightens you about (2)?",
            "How long have you been afraid?",
            "Have your fears about (2) ever come true?",
            "What would courage look like here?",
        ]),
        ("* i am afraid *", [
            "Fear deserves respect. Tell me about (2).",
            "Who comforts you when you are afraid?",
        ]),
    ]},
    {"word": "mother", "rank": 7, "rules": [
        ("* mother *", [
            "Tell me more about your mother.",
            "How do you get along with your mother?",
            "What comes to mind when you think of your mother and (2)?",
            "Does your mother know about (2)?",
            "I will remember what you shared about your mother.",
        ]),
    ]},
    {"word": "father", "rank": 7, "rules": [
        ("* father *", [
            "Tell me more about your father.",
            "How is your relationship with your father?",
            "What does your father think about (2)?",
            "Does your father know about (2)?",
        ]),
    ]},
    {"word": "mom", "rank": 7, "rules": [
        ("* mom *", [
            "Tell me about your mom.",
            "How are things between you and your mom?",
            "What would your mom say about (2)?",
        ]),
    ]},
    {"word": "dad", "rank": 7, "rules": [
        ("* dad *", [
            "Tell me about your dad.",
            "How are things between you and your dad?",
            "What would your dad say about (2)?",
        ]),
    ]},
    {"word": "sister", "rank": 7, "rules": [
        ("* sister *", [
            "Tell me about your sister.",
            "Are you close with your sister?",
            "What does your sister think about (2)?",
        ]),
    ]},
    {"word": "brother", "rank": 7, "rules": [
        ("* brother *", [
            "Tell me about your brother.",
            "Are you and your brother close?",
            "What would your brother say about (2)?",
        ]),
    ]},
    {"word": "wife", "rank": 7, "rules": [
        ("* wife *", [
            "Tell me about your wife.",
            "How are things with your wife regarding (2)?",
            "Does your wife know how you feel about (2)?",
        ]),
    ]},
    {"word": "husband", "rank": 7, "rules": [
        ("* husband *", [
            "Tell me about your husband.",
            "How are things with your husband regarding (2)?",
            "Does your husband know how you feel about (2)?",
        ]),
    ]},
    {"word": "child", "rank": 7, "rules": [
        ("* child *", [
            "Tell me about your child.",
            "How old is your child?",
            "What worries you about your child and (2)?",
        ]),
    ]},
    {"word": "children", "rank": 7, "rules": [
        ("* children *", [
            "Tell me about your children.",
            "How many children do you have?",
            "What do your children think about (2)?",
        ]),
    ]},
    {"word": "son", "rank": 7, "rules": [
        ("* son *", [
            "Tell me about your son.",
            "How is your son doing with (2)?",
            "What does your son enjoy?",
        ]),
    ]},
    {"word": "daughter", "rank": 7, "rules": [
        ("* daughter *", [
            "Tell me about your daughter.",
            "How is your daughter doing with (2)?",
            "What does your daughter enjoy?",
        ]),
    ]},
    {"word": "parent", "rank": 7, "rules": [
        ("* parent *", [
            "Tell me about your parents.",
            "How do your parents feel about (2)?",
            "Are you close with your parents?",
        ]),
    ]},
    {"word": "family", "rank": 7, "rules": [
        ("* family *", [
            "Tell me more about your family.",
            "How does your family handle (2)?",
            "Who in your family are you closest to?",
            "I will remember what you told me about your family.",
        ]),
    ]},
    {"word": "friend", "rank": 7, "rules": [
        ("* friend *", [
            "Tell me about this friend.",
            "How long have you known them?",
            "What does your friend think about (2)?",
            "Do your friends know how you feel?",
        ]),
    ]},
    {"word": "boyfriend", "rank": 7, "rules": [
        ("* boyfriend *", [
            "Tell me about your boyfriend.",
            "How are things between you two?",
            "Does he know about (2)?",
        ]),
    ]},
    {"word": "girlfriend", "rank": 7, "rules": [
        ("* girlfriend *", [
            "Tell me about your girlfriend.",
            "How are things between you two?",
            "Does she know about (2)?",
        ]),
    ]},
    {"word": "marriage", "rank": 6, "rules": [
        ("* marriage *", [
            "What does marriage mean to you in the context of (2)?",
            "How long have you been thinking about marriage?",
            "What would a good marriage look like to you?",
        ]),
    ]},
    {"word": "divorce", "rank": 6, "rules": [
        ("* divorce *", [
            "Divorce is difficult. What happened with (2)?",
            "How are you coping with the divorce?",
            "Who supports you through this?",
        ]),
    ]},
    {"word": "work", "rank": 5, "rules": [
        ("* work *", [
            "Tell me about your work and (2).",
            "Do you enjoy your work?",
            "What would better work look like?",
            "How does work affect the rest of your life?",
        ]),
    ]},
    {"word": "job", "rank": 5, "rules": [
        ("* job *", [
            "How is the job going with (2)?",
            "Do you feel valued at your job?",
            "Would you change jobs if you could?",
        ]),
    ]},
    {"word": "boss", "rank": 5, "rules": [
        ("* boss *", [
            "Tell me about your boss.",
            "What does your boss do about (2)?",
            "How do you handle conflict with your boss?",
        ]),
    ]},
    {"word": "school", "rank": 5, "rules": [
        ("* school *", [
            "Tell me about school and (2).",
            "Do you enjoy school?",
            "What subjects speak to you?",
        ]),
    ]},
    {"word": "teacher", "rank": 5, "rules": [
        ("* teacher *", [
            "Tell me about your teacher.",
            "What did your teacher say about (2)?",
            "Do you respect your teacher?",
        ]),
    ]},
    {"word": "exam", "rank": 5, "rules": [
        ("* exam *", [
            "Exams are stressful. How are you preparing for (2)?",
            "What worries you about the exam?",
            "What happens after the exam?",
        ]),
    ]},
    {"word": "money", "rank": 5, "rules": [
        ("* money *", [
            "Money worries weigh heavily. Tell me about (2).",
            "How does money shape (2)?",
            "What would enough money change?",
            "Who do you talk to about money?",
        ]),
    ]},
    {"word": "debt", "rank": 5, "rules": [
        ("* debt *", [
            "Debt is stressful. How did (2) come about?",
            "What is your plan for the debt?",
            "Who knows about this debt?",
        ]),
    ]},
    {"word": "health", "rank": 5, "rules": [
        ("* health *", [
            "Tell me about your health and (2).",
            "Are you taking care of yourself?",
            "What does your body need right now?",
        ]),
    ]},
    {"word": "doctor", "rank": 5, "rules": [
        ("* doctor *", [
            "Doctors can help. What did yours say about (2)?",
            "Do you trust your doctor?",
            "I am a program, not a medical doctor. Please see a real one for health worries.",
        ]),
    ]},
    {"word": "therapist", "rank": 5, "rules": [
        ("* therapist *", [
            "Therapy takes courage. What do you explore with (2)?",
            "What does your therapist say?",
            "I am only a simple program, a real therapist can help more.",
        ]),
    ]},
    {"word": "sleep", "rank": 4, "rules": [
        ("* sleep *", [
            "How are you sleeping lately?",
            "What keeps you up about (2)?",
            "Do you dream about (2)?",
        ]),
    ]},
    {"word": "food", "rank": 4, "rules": [
        ("* food *", [
            "Tell me about food and (2).",
            "Do you cook?",
            "What comfort food gets you through (2)?",
        ]),
    ]},
    {"word": "music", "rank": 4, "rules": [
        ("* music *", [
            "What music moves you when (2)?",
            "Do you play an instrument?",
            "What song describes (2)?",
        ]),
    ]},
    {"word": "movie", "rank": 4, "rules": [
        ("* movie *", [
            "What movie reminds you of (2)?",
            "Do you watch movies to escape or to feel?",
            "Who would you watch (2) with?",
        ]),
    ]},
    {"word": "book", "rank": 4, "rules": [
        ("* book *", [
            "What book speaks to (2)?",
            "Do you read to escape?",
            "What did you last read about (2)?",
        ]),
    ]},
    {"word": "sport", "rank": 4, "rules": [
        ("* sport *", [
            "Do you play (2)?",
            "What does sport give you?",
            "Team or solo, and why?",
        ]),
    ]},
    {"word": "game", "rank": 4, "rules": [
        ("* game *", [
            "Games reveal us. What draws you to (2)?",
            "Do you play to win or to unwind?",
            "Have you tried the GameBored arcade lately?",
        ]),
    ]},
    {"word": "gamebored", "rank": 9, "rules": [
        ("* gamebored *", [
            "GameBored is a fine distraction. Which game is yours?",
            "Do the games help with (2), or just pass time?",
            "I hear the desktop remembers your last pick. What is yours?",
        ]),
    ]},
    {"word": "computer", "rank": 6, "rules": [
        ("* computer *", [
            "Do computers worry you about (2)?",
            "Why do you mention computers?",
            "Do you think machines like me can understand (2)?",
            "What do computers symbolize to you?",
        ]),
    ]},
    {"word": "phone", "rank": 5, "rules": [
        ("* phone *", [
            "Who calls you about (2)?",
            "Do you wish the phone would ring, or stay silent?",
            "What would you say if you called about (2)?",
        ]),
    ]},
    {"word": "internet", "rank": 5, "rules": [
        ("* internet *", [
            "The internet knows everything and nothing. What did it tell you about (2)?",
            "Do you trust what you read about (2)?",
            "Does being online about (2) help or hurt?",
        ]),
    ]},
    {"word": "death", "rank": 7, "rules": [
        ("* death *", [
            "Death is profound. What brings it to mind with (2)?",
            "Are you grieving someone?",
            "What does mortality mean to you right now?",
        ]),
    ]},
    {"word": "died", "rank": 7, "rules": [
        ("* died *", [
            "I am sorry for your loss. Who died?",
            "How long ago did (2) die?",
            "What do you miss most?",
            "Grief has no schedule. How are you coping?",
        ]),
    ]},
    {"word": "grief", "rank": 7, "rules": [
        ("* grief *", [
            "Grief comes in waves. Where are you with (2)?",
            "Who supports your grief?",
            "What honors what was lost?",
        ]),
    ]},
    {"word": "sex", "rank": 6, "rules": [
        ("* sex *", [
            "Sex can be complicated. What about (2) is on your mind?",
            "How do you feel discussing this?",
            "Is this about intimacy, or something else?",
        ]),
    ]},
    {"word": "why", "rank": 8, "rules": [
        ("* why *", [
            "Why do you ask about (2)?",
            "What answer would satisfy you about (2)?",
            "Have you asked yourself that before?",
            "What theories do you already have about (2)?",
        ]),
    ]},
    {"word": "what", "rank": 8, "rules": [
        ("* what *", [
            "What do you think about (2)?",
            "Why does (2) matter to you?",
            "If you knew (2), what would change?",
        ]),
    ]},
    {"word": "how", "rank": 8, "rules": [
        ("* how *", [
            "How do you suppose (2)?",
            "What makes you ask how (2)?",
            "How would you like (2) to go?",
        ]),
    ]},
    {"word": "who", "rank": 8, "rules": [
        ("* who *", [
            "Who do you have in mind with (2)?",
            "Are you asking about yourself?",
            "Who else is involved in (2)?",
        ]),
    ]},
    {"word": "where", "rank": 8, "rules": [
        ("* where *", [
            "Where do you imagine (2)?",
            "Does the place matter for (2)?",
            "Where would you rather be?",
        ]),
    ]},
    {"word": "when", "rank": 8, "rules": [
        ("* when *", [
            "When did (2) start?",
            "What timing would be right for (2)?",
            "Does it feel urgent?",
        ]),
    ]},
    {"word": "because", "rank": 7, "rules": [
        ("* because *", [
            "Is that the real reason, (2)?",
            "What other reasons might there be?",
            "Does that reason satisfy you?",
        ]),
    ]},
    {"word": "can", "rank": 4, "rules": [
        ("* can you *", [
            "Perhaps I can (2). What would that mean to you?",
            "Why do you ask whether I can (2)?",
            "Do you believe anyone can (2)?",
        ]),
        ("* can i *", [
            "Perhaps you can (2). What stops you?",
            "Do you want to be able to (2)?",
            "What if you could (2)?",
        ]),
        ("* can *", [
            "What would it take to (2)?",
            "Is (2) truly possible?",
        ]),
    ]},
    {"word": "will", "rank": 3, "rules": [
        ("* will *", [
            "What makes you think (2) will happen?",
            "Would you welcome it if (2)?",
            "What if it never does?",
        ]),
    ]},
    {"word": "maybe", "rank": 3, "rules": [
        ("*", [
            "Why the uncertain tone?",
            "Can you be more definite?",
            "Maybe, maybe not. What do you lean toward?",
        ]),
    ]},
    {"word": "perhaps", "rank": 3, "rules": [
        ("*", [
            "Why so tentative?",
            "You do not seem certain. What wavers?",
            "Perhaps. What would certainty feel like?",
        ]),
    ]},
]


def keyword_count():
    """Number of keywords in the script."""
    return len(KEYWORDS)


def reassembly_count():
    """Total number of reassembly rules across the whole script."""
    total = 0
    for entry in KEYWORDS:
        for _decomp, reassemblies in entry.get("rules", []):
            total += len(reassemblies)
    return total
