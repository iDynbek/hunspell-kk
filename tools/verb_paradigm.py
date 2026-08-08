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
STEMS = ["оқы", "сөйле", "кел", "ал", "көр", "бер", "айт", "жаз", "кет", "сат"]


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


def before_u(stem: str) -> str:
    """A stem-final `ы`/`і` is lost before `-у`: `оқы` gives `оқу`, not `оқыу`."""
    return stem[:-1] if stem[-1:] in "ыі" else stem


def present_stem(stem: str) -> str:
    """The present converb: `кел` + `-е`, `айт` + `-а`, and `оқы` → `оқи`.

    A stem-final `ы`/`і` does not survive in front of the glide; the two fuse
    and are written `и`. Getting this wrong produces `оқый`, which no Kazakh
    text contains — which is how the validation pass catches it.
    """
    if stem[-1] in "ыі":
        return stem[:-1] + "и"
    if vowel_final(stem):
        return stem + "й"
    return stem + pick("а", "е", stem)


# `-мын` after the present and the participles; bare `-м` after the definite
# past and the conditional. Kazakh keeps the two apart and so must this.
FULL_PERSON = (("1sg", "мын", "мін"), ("2sg", "сың", "сің"), ("2pol", "сыз", "сіз"),
               ("3", "", ""), ("1pl", "мыз", "міз"),
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
        "pres": (present, FULL_PERSON, present + pick("ды", "ді", stem)),
        "past": (stem + past, SHORT_PERSON, None),
        "perf": (stem + perfect, FULL_PERSON, None),
        "cond": (stem + pick("са", "се", stem), SHORT_PERSON, None),
        "fut": (stem + presumptive, FULL_PERSON, None),
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
        ("inf", before_u(stem) + "у"),
        ("part.past", stem + perfect),
        ("part.hab", present_stem(stem) + pick("тын", "тін", stem)),
        ("part.agent", before_u(stem) + pick("ушы", "уші", stem)),
        ("conv.ip", converb),
        ("conv.a", present_stem(stem)),
        ("conv.gali", stem + (pick("қалы", "келі", stem) if voiceless
                              else pick("ғалы", "гелі", stem))),
        ("hearsay", converb + pick("ты", "ті", stem)),
    ]


def paradigm(stem: str) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for polarity, base in (("pos", stem), ("neg", stem + negation(stem))):
        for tense, (form, persons, third) in tenses(base).items():
            for name, back, front in persons:
                word = third if (name == "3" and third) else form + pick(back, front, base)
                out.append((f"{polarity}.{tense}.{name}", word))
        out += [(f"{polarity}.{label}", word) for label, word in nonfinite(base)]
    out += [(label, word) for label, word in imperatives(stem)]
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dictionaries", type=Path, nargs="*")
    ap.add_argument("--write", type=Path)
    ap.add_argument("--residues", type=Path)
    ap.add_argument("--weight", type=int, default=60)
    ap.add_argument("--validate", action="store_true",
                    help="report which generated forms KazNERD never contains")
    ap.add_argument("--kaznerd", type=Path, default=ROOT.parent / "KazNERD/KazNERD")
    args = ap.parse_args()

    grid = [(stem, label, form) for stem in STEMS for label, form in paradigm(stem)]

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
        for stem in STEMS:
            cls = "v" + stem_class(stem)
            for _label, form in paradigm(stem):
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
