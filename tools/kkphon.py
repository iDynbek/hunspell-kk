"""Which shape a Kazakh suffix takes, and what decides it.

Two things pick the shape. Vowel harmony picks the vowels, from the last vowel
in the stem however far back that is. The stem's final segment picks the
initial consonant: `бала-лар`, `жол-дар`, `мектеп-тер` are one morpheme in
three shapes.

The 2009 affix file encodes both in each rule's condition, which is where its
two worst bugs come from. A condition can only look at a fixed window of the
stem, so `[аоуұыэ]т` matches `ат` but not `спорт`, and 6,521 forms are lost to
stems ending in a consonant cluster. And because the same consonant list has to
be retyped for every suffix in both harmonies, one of them was left short: the
back-harmony plural covers `бвгғдт` where the front covers `бвгғдкқһпстфхцчшщ`,
so `халықтар`, `кітаптар` and `достар` are rejected — 26,803 forms.

Classifying the stem once, at the entry, and putting the answer in its flags
removes both failure modes: the affix rules stop guessing at what they cannot
see.
"""

from __future__ import annotations

# Orthographic vowels. `у` and `ю` are also consonantal, which is why they get
# their own final class below rather than counting as vowel-final.
BACK_VOWELS = frozenset("аоуұыэ")
FRONT_VOWELS = frozenset("әеёиөүіюя")
VOWELS = BACK_VOWELS | FRONT_VOWELS

# Final-segment classes, named for the plural allomorph each one selects.
FINAL_V = "v"   # a vowel                        бала  → балалар, баланың
FINAL_R = "r"   # й р у ю                        бай   → байлар,  байдың
FINAL_Z = "z"   # ж з л                          жол   → жолдар,  жолдың
FINAL_N = "n"   # м н ң                          адам  → адамдар, адамның
FINAL_T = "t"   # any voiceless consonant        мектеп → мектептер, мектептің

# The nasals need their own class even though they take the same plural as
# ж/з/л: the genitive splits them, `адамның` against `жолдың`. One four-way
# class cannot serve both suffixes, and merging them is what let `адалның`
# through.
FINAL_CONSONANTS = {
    FINAL_R: frozenset("йрую"),
    FINAL_Z: frozenset("жзл"),
    FINAL_N: frozenset("мнң"),
    FINAL_T: frozenset("бвгғдкқпстфхһцчшщ"),
}

HARM_BACK = "b"
HARM_FRONT = "f"

# Vowels that do not settle the question. `и`, `э`, `ю` and `я` are written for
# sequences that can go either way. `у` is the infinitive marker, and it takes
# the harmony of what comes before it rather than supplying its own — `беру`
# and `елу` are front despite ending in a back vowel, and inflect `беруге`,
# `елуге`. Where the last vowel is one of these the vowel before it decides; if
# there is none, back is the safer default, being the larger inventory.
AMBIGUOUS_VOWELS = frozenset("иэюяу")


def harmony(word: str) -> str:
    """Back or front, from the last vowel that commits to one."""
    for ch in reversed(word):
        if ch in AMBIGUOUS_VOWELS:
            continue
        if ch in BACK_VOWELS:
            return HARM_BACK
        if ch in FRONT_VOWELS:
            return HARM_FRONT
    return HARM_BACK


# A soft or hard sign is not a segment of its own; it modifies the consonant
# in front of it. Reading it as a consonant makes every Russian loan ending in
# -ль or -нь take the voiceless suffix — `*моральқа` for `моральға`.
SIGNS = frozenset("ьъ")


def final_class(word: str) -> str:
    """Which consonant the next suffix starts with."""
    word = word.rstrip("".join(SIGNS))
    if not word:
        return FINAL_V
    last = word[-1]
    for name, members in FINAL_CONSONANTS.items():
        if last in members:
            return name
    return FINAL_V if last in VOWELS else FINAL_T


def stem_class(word: str) -> str:
    """The pair as one token, e.g. `bt` for back harmony, voiceless final."""
    return harmony(word) + final_class(word)


CLASSES = tuple(h + f for h in (HARM_BACK, HARM_FRONT)
                for f in (FINAL_V, FINAL_R, FINAL_Z, FINAL_N, FINAL_T))
