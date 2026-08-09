"""Generate the finite verb paradigm, and check the dictionary has it.

The nominal grid turned out to be 83.9% covered before it was tested and 100%
after. The verbal grid is the larger of the two and had never been looked at.

Kazakh finite verbs are tense × person × polarity, with two different person
sets — `-мын`/`-сың` after the present and the participles, bare `-м`/`-ң`
after the definite past and the conditional — and a stem that changes shape
before a vowel: `оқы` plus `-й` is `оқи`, not `оқый`.

Unlike the nominal grid there is no hand-written reference to check against, so
the forms are validated by looking for them in KazNERD: a generated form that
real Kazakh text never contains is most likely the generator's mistake.

    python tools/verb_paradigm.py --validate
    python tools/verb_paradigm.py dict/kk_KZ
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from kkphon import harmony  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

VOWELS = frozenset("аәеоөұүыіиуюяё")
VOICELESS = frozenset("бвгғдкқпстфхһцчшщ")
SIBILANT = frozenset("жз")

# Vowel-final, sonorant-final and voiceless-final, in both harmonies.
#
# `тап` is deliberately absent although it fits the last class: it is
# irregular, giving `тауып` rather than `тапып` before a vowel and `табу`
# rather than `тапу` in the infinitive. A grid of regular stems should not be
# asked to predict it, and the first run of this test blamed the dictionary for
# four forms that were the generator's fault.
STEMS = ["оқы", "сөйле", "кел", "ал", "көр", "бер", "айт", "жаз", "кет",
         "сат", "сез", "аш", "тұрғыз"]  # сез/аш/тұрғыз cover з/ш-final passive allomorphs


def pick(back: str, front: str, stem: str) -> str:
    return back if harmony(stem) == "b" else front


def vowel_final(stem: str) -> bool:
    return stem[-1] in VOWELS


def negation(stem: str) -> str:
    """`-ма` after a sonorant, `-ба` after ж/з, `-па` after a voiceless stop."""
    last = stem[-1]
    if last in SIBILANT:
        return pick("ба", "бе", stem)
    if last in VOICELESS:
        return pick("па", "пе", stem)
    return pick("ма", "ме", stem)


SONORANT = frozenset("лмнңр")


def voices(stem: str) -> list[tuple[str, str]]:
    """The voice stems a verb derives, each a new verb in its own right.

    Kazakh builds passive, reflexive, reciprocal and causative stems with
    suffixes that then take the whole tense and person grid on top — `жаз`,
    `жазыл`, `жазылады`, `жазылмағанмын`. The allomorphs go by the stem's last
    segment, and the passive is the awkward one: after `л` it is `-ын`, not
    `-ыл`, because `аллын` is not pronounceable.
    """
    last = stem[-1]
    vowel = vowel_final(stem)

    if vowel:
        passive = stem + "л"
    elif last == "л":
        passive = stem + pick("ын", "ін", stem)
    else:
        passive = stem + pick("ыл", "іл", stem)

    reflexive = stem + ("н" if vowel else pick("ын", "ін", stem))
    reciprocal = stem + ("с" if vowel else pick("ыс", "іс", stem))

    if vowel:
        causative = stem + "т"
    elif last in VOICELESS:
        causative = stem + pick("тыр", "тір", stem)
    elif last == "р":
        causative = stem + pick("ғыз", "гіз", stem)
    else:
        causative = stem + pick("дыр", "дір", stem)

    return [("pass", passive), ("refl", reflexive),
            ("recip", reciprocal), ("caus", causative)]


def before_u(stem: str) -> str:
    """A stem-final `ы`/`і` is lost before `-у`: `оқы` gives `оқу`, not `оқыу`."""
    return stem[:-1] if stem[-1:] in "ыі" else stem


def u_form(stem: str) -> str:
    """The verbal noun / infinitive: `оқу`, `жазу`, and `жою` from `жой`.

    A final `й` fuses with the `-у` into `ю`, so the infinitive of `жой` is
    `жою`, not `жойу`; the declined verbal noun then runs off that.
    """
    if stem[-1] == "й":
        return stem[:-1] + "ю"
    return before_u(stem) + "у"


def glide_present(stem: str) -> str | None:
    """`жой` + a vowel absorbs the `й`: `жоя`, not `жойа`. Every `й`-final verb
    does this — `қой` → `қояды`, `той` → `тояды`, `сой` → `сояды`."""
    if len(stem) >= 3 and stem[-1] == "й":
        return stem[:-1] + pick("я", "е", stem)
    return None


def present_stem(stem: str) -> str:
    """The present converb: `кел` + `-е`, `айт` + `-а`, and `оқы` → `оқи`.

    A stem-final `ы`/`і` does not survive in front of the glide; the two fuse
    and are written `и`. Getting this wrong produces `оқый`, which no Kazakh
    text contains — which is how the validation pass catches it.
    """
    glide = glide_present(stem)
    if glide:
        return glide
    if stem[-1] in "ыі":
        return stem[:-1] + "и"
    if vowel_final(stem):
        return stem + "й"
    return stem + pick("а", "е", stem)


# The copula person endings — `-мын`, `-мыз` — carry the allomorph the whole
# language does: `-м` only after a vowel, `-б` after a voiced consonant, `-п`
# after a voiceless one. So the present, which attaches after a vowel, is
# `оқимын`, but the perfect after `-ған` is `оқығанбыз` not `оқығанмыз`, and the
# negative future after `-мас` is `оқымаспын` not `оқымасмын`. Apertium caught
# both; KazNERD had not, because the 1pl perfect is rare in news.


def full_person(base: str) -> tuple:
    """The predicative person endings, whose 1sg/1pl allomorph Apertium pinned.

    The 1sg is `-мын` everywhere but after a voiceless consonant, where it is
    `-пын` (`оқымаспын`). The 1pl agrees except after the perfect participle
    `-ған`/`-ген`, where it is uniquely `-быз` (`оқығанбыз`, not `*оқығанмыз`) —
    an irregularity the phonology does not predict and the news corpus never
    showed.
    """
    voiceless = base[-1] in "кқптсшщфхһцч"
    sg = "п" if voiceless else "м"
    pl = "п" if voiceless else ("б" if base.endswith(("ған", "ген",
                                                      "қан", "кен")) else "м")
    return (("1sg", sg + "ын", sg + "ін"), ("2sg", "сың", "сің"),
            ("2pol", "сыз", "сіз"), ("3", "", ""), ("1pl", pl + "ыз", pl + "із"),
            ("2pl", "сыңдар", "сіңдер"), ("2polpl", "сыздар", "сіздер"))


SHORT_PERSON = (("1sg", "м", "м"), ("2sg", "ң", "ң"), ("2pol", "ңыз", "ңіз"),
                ("3", "", ""), ("1pl", "қ", "к"),
                ("2pl", "ңдар", "ңдер"), ("2polpl", "ңыздар", "ңіздер"))


def tenses(stem: str) -> dict[str, tuple[str, tuple]]:
    """Tense stem → (form the person endings attach to, which person set)."""
    voiceless = stem[-1] in VOICELESS
    past = (pick("ты", "ті", stem) if voiceless else pick("ды", "ді", stem))
    perfect = (pick("қан", "кен", stem) if voiceless else pick("ған", "ген", stem))
    # The negative aorist is `-с`, not the `-р` of the positive: `оқымас`,
    # `келмес`, `айтпас`. Attaching `-р` to a negated stem gives `оқымар`,
    # which is what the validation pass flagged.
    if stem.endswith(("ма", "ме", "ба", "бе", "па", "пе")):
        presumptive = "с"
    else:
        presumptive = "р" if vowel_final(stem) else pick("ар", "ер", stem)
    # The present is the one tense whose third person is not bare: `келеді`,
    # `айтады`, `оқиды`. Everywhere else the third person is the tense stem.
    present = present_stem(stem)
    return {
        "pres": (present, full_person(present), present + pick("ды", "ді", stem)),
        "past": (stem + past, SHORT_PERSON, None),
        "perf": (stem + perfect, full_person(stem + perfect), None),
        "cond": (stem + pick("са", "се", stem), SHORT_PERSON, None),
        "fut": (stem + presumptive, full_person(stem + presumptive), None),
    }


def imperatives(stem: str) -> list[tuple[str, str]]:
    if vowel_final(stem):
        base = present_stem(stem)          # оқи-, сөйлей-
        return [("imp.2sg", stem),
                ("imp.2pol", stem + pick("ңыз", "ңіз", stem)),
                ("imp.1sg", base + pick("ын", "ін", stem)),
                ("imp.1pl", base + pick("ық", "ік", stem)),
                ("imp.2pl", stem + pick("ңдар", "ңдер", stem))]
    return [("imp.2sg", stem),
            ("imp.2pol", stem + pick("ыңыз", "іңіз", stem)),
            ("imp.1sg", stem + pick("айын", "ейін", stem)),
            ("imp.1pl", stem + pick("айық", "ейік", stem)),
            ("imp.2pl", stem + pick("ыңдар", "іңдер", stem))]


def nonfinite(stem: str) -> list[tuple[str, str]]:
    voiceless = stem[-1] in VOICELESS
    perfect = pick("қан", "кен", stem) if voiceless else pick("ған", "ген", stem)
    converb = (stem + pick("п", "п", stem) if vowel_final(stem)
               else stem + pick("ып", "іп", stem))
    return [
        ("inf", u_form(stem)),
        ("part.past", stem + perfect),
        ("part.hab", present_stem(stem) + pick("тын", "тін", stem)),
        ("part.agent", before_u(stem) + pick("ушы", "уші", stem)),
        ("conv.ip", converb),
        ("conv.a", present_stem(stem)),
        ("conv.gali", stem + (pick("қалы", "келі", stem) if voiceless
                              else pick("ғалы", "гелі", stem))),
        ("hearsay", converb + pick("ты", "ті", stem)),
    ]


# The participles decline. `-ған` (perfect) and `-атын`/`-йтін` (habitual) are
# deverbal, and take the whole case grid and plural like an adjective:
# `құрылғанға`, `ашқандарға`, `істейтіндерге`, `кетірілгендерден`. This is
# everywhere in legal Kazakh — a clause modifying a noun becomes a case-marked
# participle — and the paradigm had only the bare participle.
PARTICIPLE_CASES = (
    ("dat", "ға", "ге"), ("loc", "да", "де"), ("abl", "нан", "нен"),
    ("gen", "ның", "нің"), ("acc", "ды", "ді"), ("ins", "мен", "мен"),
    ("p3", "ы", "і"), ("p3.acc", "ын", "ін"), ("p3.dat", "ына", "іне"),
    ("p3.loc", "ында", "інде"), ("p3.abl", "ынан", "інен"),
    ("pl", "дар", "дер"), ("pl.dat", "дарға", "дерге"),
    ("pl.gen", "дардың", "дердің"), ("pl.acc", "дарды", "дерді"),
    ("pl.abl", "дардан", "дерден"), ("pl.loc", "дарда", "дерде"),
)


def participles(stem: str) -> list[tuple[str, str]]:
    voiceless = stem[-1] in VOICELESS
    perfect = stem + (pick("қан", "кен", stem) if voiceless
                      else pick("ған", "ген", stem))
    habitual = present_stem(stem) + pick("тын", "тін", stem)
    out = []
    for base, tag in ((perfect, "past"), (habitual, "hab")):
        for label, back, front in PARTICIPLE_CASES:
            # The habitual `-тын` ends in `-н` and so takes the `-н-` series
            # dative — `оқитына`, not `*оқитынға`, exactly as a noun after a
            # third-person possessive does.
            if tag == "hab" and label == "dat":
                out.append((f"part.{tag}.{label}", base + pick("а", "е", stem)))
            else:
                out.append((f"part.{tag}.{label}", base + pick(back, front, stem)))
    return out


# The verbal noun `-у` is a noun and takes the whole case grid on top: `жасау`
# gives `жасауға`, `жасауда`, `жасауы`, `жасауын`, `жасауымен`. This is one of
# the commonest constructions in formal Kazakh — `қабылдануға`, `қатыспауы` —
# and it applies to voice stems too, so a paradigm that stopped at the bare
# infinitive missed a whole productive layer. The endings are the vowel-final
# nominal set, since `-у` ends the word in a vowel-like segment.
VERBAL_NOUN_CASES = (
    ("nom", ""), ("gen", "дың"), ("dat", "ға"), ("acc", "ды"), ("loc", "да"),
    ("abl", "дан"), ("ins", "мен"), ("pl", "лар"), ("pl.gen", "лардың"),
    ("pl.dat", "ларға"), ("pl.acc", "ларды"),
    ("p3", "ы"), ("p3.acc", "ын"), ("p3.dat", "ына"), ("p3.loc", "ында"),
    ("p3.abl", "ынан"), ("p3.gen", "ының"), ("p1", "ым"), ("p2", "ың"),
    ("p1pl", "ымыз"), ("p2pol", "ыңыз"),
)


def verbal_noun(stem: str) -> list[tuple[str, str]]:
    noun = u_form(stem)
    return [(f"vn.{label}", noun + pick(suf, _front(suf), stem))
            for label, suf in VERBAL_NOUN_CASES]


def _front(back: str) -> str:
    return back.translate(str.maketrans("аоұығқ", "еөүігк"))


# The desiderative `-ғы`/`-қы` is a "want to" participle that only ever appears
# under a possessive: `айтқым (келеді)` "I want to say", `кеткісі бар` "wants to
# leave". The suffix voices like the past — `-қы`/`-кі` after a voiceless stop,
# `-ғы`/`-гі` otherwise — and the whole thing takes a possessive, positive and
# negative alike (`айтпағым`). Pervasive in dialogue, so the news corpus was
# thin on it; Apertium confirms the possessive forms but not a case on top.
DESIDERATIVE_POSS = (("p1sg", "м", "м"), ("p2sg", "ң", "ң"),
                     ("p2pol", "ңыз", "ңіз"), ("p3", "сы", "сі"),
                     ("p1pl", "мыз", "міз"))


def desiderative(base: str) -> list[tuple[str, str]]:
    suffix = (pick("қы", "кі", base) if base[-1] in VOICELESS
              else pick("ғы", "гі", base))
    stem = base + suffix
    return [(f"desid.{name}", stem + pick(back, front, base))
            for name, back, front in DESIDERATIVE_POSS]


# The softener `-шы`/`-ші` is an emphatic clitic on a request: `айтшы` "do say",
# `айтыңызшы`, `айтсаңшы` "why don't you say". It attaches to the second-person
# imperative and conditional, harmonising only, and like the desiderative it is a
# dialogue form the news corpus barely carries.
def softener(stem: str) -> list[tuple[str, str]]:
    emph = pick("шы", "ші", stem)
    imp = dict(imperatives(stem))
    cond = stem + pick("са", "се", stem)
    bases = (("2sg", stem),
             ("2pol", imp["imp.2pol"]),
             ("cond.2sg", cond + "ң"),
             ("cond.2pol", cond + pick("ңыз", "ңіз", stem)))
    return [(f"soft.{name}", base + emph) for name, base in bases]


def paradigm(stem: str) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for polarity, base in (("pos", stem), ("neg", stem + negation(stem))):
        for tense, (form, persons, third) in tenses(base).items():
            for name, back, front in persons:
                word = third if (name == "3" and third) else form + pick(back, front, base)
                out.append((f"{polarity}.{tense}.{name}", word))
        out += [(f"{polarity}.{label}", word) for label, word in nonfinite(base)]
        out += [(f"{polarity}.{label}", word) for label, word in verbal_noun(base)]
        out += [(f"{polarity}.{label}", word) for label, word in participles(base)]
        out += [(f"{polarity}.{label}", word) for label, word in desiderative(base)]
    out += [(label, word) for label, word in imperatives(stem)]
    out += [(label, word) for label, word in softener(stem)]
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dictionaries", type=Path, nargs="*")
    ap.add_argument("--write", type=Path)
    ap.add_argument("--residues", type=Path)
    ap.add_argument("--weight", type=int, default=60)
    ap.add_argument("--voices", action="store_true",
                    help="also run the grid over passive, reflexive, reciprocal "
                         "and causative stems")
    ap.add_argument("--validate", action="store_true",
                    help="report which generated forms KazNERD never contains")
    ap.add_argument("--kaznerd", type=Path, default=ROOT.parent / "KazNERD/KazNERD")
    args = ap.parse_args()

    grid = [(stem, label, form) for stem in STEMS for label, form in paradigm(stem)]
    kept = []
    if args.voices:
        # Voice is derivational, not inflectional: `оқы` has no reflexive and
        # `сөйле` no passive, and which verbs have which is lexical. Only the
        # voice stems the language actually uses are kept — attested in
        # KazNERD or present in the wordlist.
        from measure_running import tokens
        from gen_dic import read_lexicon
        real = ({w.lower() for w in tokens(args.kaznerd, "*")}
                if args.kaznerd.exists() else set())
        real |= set(read_lexicon(ROOT / "data/lexicon.tsv"))
        kept = [(stem, voice, derived) for stem in STEMS
                for voice, derived in voices(stem) if derived in real]
        print(f"{len(kept)} of {len(STEMS) * 4} voice stems exist",
              file=sys.stderr)
        grid += [(stem, f"{voice}.{label}", form)
                 for stem, voice, derived in kept
                 for label, form in paradigm(derived)]

    if args.validate:
        from measure_running import tokens
        seen = {w.lower() for w in tokens(args.kaznerd, "*")}
        missing = [(s, l, f) for s, l, f in grid if f not in seen]
        print(f"{len(grid) - len(missing):,}/{len(grid):,} generated forms occur "
              f"in KazNERD ({(1 - len(missing) / len(grid)) * 100:.0f}%)")
        by_cell: dict[str, int] = {}
        for _s, label, _f in missing:
            by_cell[label.split(".", 1)[-1]] = by_cell.get(label.split(".", 1)[-1], 0) + 1
        print("  cells least attested: " + ", ".join(
            f"{c} ({n}/{len(STEMS) * 2})" for c, n in
            sorted(by_cell.items(), key=lambda kv: -kv[1])[:8]))
        print("  examples: " + ", ".join(f for _s, _l, f in missing[:12]))

    if args.write:
        args.write.parent.mkdir(parents=True, exist_ok=True)
        with args.write.open("w", encoding="utf-8") as fh:
            fh.write("# stem\tcell\tform — generated by tools/verb_paradigm.py\n")
            for stem, label, form in grid:
                fh.write(f"{stem}\t{label}\t{form}\n")
        print(f"{len(grid):,} forms over {len(STEMS)} stems → {args.write}",
              file=sys.stderr)

    if args.residues:
        from kkphon import stem_class
        rows = set()
        # Residues are taken against the base stem, so the chain carries the
        # voice suffix with it: `жаз` to `жазылады` is the residue `ылады`.
        by_stem = {s: [f for _l, f in paradigm(s)] for s in STEMS}
        for stem, _voice, derived in kept:
            by_stem[stem] = by_stem[stem] + [f for _l, f in paradigm(derived)]
        for stem in STEMS:
            cls = "v" + stem_class(stem)
            for form in by_stem[stem]:
                if form == stem:
                    continue
                # A general strip, not the narrow one mine_residues computes:
                # `оқы` becomes `оқи` before the glide, so the rule has to take
                # `ы` off and put `имын` on, and nothing about that is voicing
                # or elision.
                shared = 0
                while (shared < min(len(stem), len(form))
                       and stem[shared] == form[shared]):
                    shared += 1
                strip, residue = stem[shared:], form[shared:]
                if residue and len(strip) <= 2:
                    rows.add((cls, strip or "0", residue))
        with args.residues.open("w", encoding="utf-8") as fh:
            fh.write("# class\tstrip\tresidue\tcount — from tools/verb_paradigm.py\n")
            for cls, strip, residue in sorted(rows):
                fh.write(f"{cls}\t{strip}\t{residue}\t{args.weight}\n")
        print(f"{len(rows):,} verb residues → {args.residues}", file=sys.stderr)

    for base in args.dictionaries:
        forms = [f for _s, _l, f in grid]
        proc = subprocess.run(["hunspell", "-d", str(base), "-l"],
                              input="\n".join(forms), capture_output=True, text=True)
        missing = set(proc.stdout.split())
        print(f"\n{base}: {len(forms) - len(missing):,}/{len(forms):,} "
              f"({(1 - len(missing) / len(forms)) * 100:.1f}%)")
        by_stem: dict[str, list[str]] = {}
        for stem, label, form in grid:
            if form in missing:
                by_stem.setdefault(stem, []).append(f"{label}={form}")
        for stem, gaps in sorted(by_stem.items(), key=lambda kv: -len(kv[1]))[:5]:
            print(f"  {stem:<8} {len(gaps):>3} missing: {', '.join(gaps[:4])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
