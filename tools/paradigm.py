"""Generate the full nominal paradigm of a word, and check the dictionary has it.

Corpus recall cannot tell "the language does not do this" from "the corpus did
not happen to". A paradigm can: Kazakh nominal inflection is a closed grid of
number, possessive and case, so every cell either exists or does not, and a
dictionary either reaches it or does not.

The forms are built here from the allomorph rules directly, not from the affix
file, so this is a test rather than a restatement. The rules are the ordinary
ones — plural chosen by the stem's final segment, case chosen by whatever
stands in front of it, and the `-н-` series after a third-person possessive:
`баласы` gives `баласына`, `баласында`, `баласынан`.

    python tools/paradigm.py --write tests/paradigms.tsv
    python tools/paradigm.py dict/kk_KZ baseline/kk_KZ

The stems are one per phonological class, so a gap in any class shows up.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from kkphon import FINAL_N, FINAL_R, FINAL_T, FINAL_V, FINAL_Z  # noqa: E402
from kkphon import final_class, harmony  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

# One stem per class, back and front, chosen to be ordinary and unambiguous.
STEMS = ["алма", "бала", "бай", "тау", "жол", "қыз", "адам", "сан",
         "мектеп", "кітап", "терезе", "күн", "үй", "көл", "сөз", "жүрек"]


def pick(back: str, front: str, stem: str) -> str:
    return back if harmony(stem) == "b" else front


# A stem-final voiceless stop voices before a vowel: `мектеп` is `мектебім`,
# `кітап` is `кітабым`, `жүрек` is `жүрегім`. Without this the grid asks for
# `мектепім`, which is not a word, and every dictionary rightly fails it.
VOICING = {"қ": "ғ", "к": "г", "п": "б"}
VOWELS = frozenset("аәеоөұүыіиуюяё")


def join(stem: str, suffix: str) -> str:
    if suffix[:1] in VOWELS and stem[-1:] in VOICING:
        return stem[:-1] + VOICING[stem[-1]] + suffix
    return stem + suffix


def plural(stem: str) -> str:
    cls = final_class(stem)
    if cls in (FINAL_V, FINAL_R):
        return pick("лар", "лер", stem)
    if cls in (FINAL_Z, FINAL_N):
        return pick("дар", "дер", stem)
    return pick("тар", "тер", stem)


def possessives(stem: str) -> dict[str, str]:
    """After a vowel the linking vowel is dropped: `алма+м`, not `алма+ым`."""
    vowel = final_class(stem) == FINAL_V
    return {
        "1sg": pick("м", "м", stem) if vowel else pick("ым", "ім", stem),
        "2sg": pick("ң", "ң", stem) if vowel else pick("ың", "ің", stem),
        "2pol": pick("ңыз", "ңіз", stem) if vowel else pick("ыңыз", "іңіз", stem),
        "3": pick("сы", "сі", stem) if vowel else pick("ы", "і", stem),
        "1pl": pick("мыз", "міз", stem) if vowel else pick("ымыз", "іміз", stem),
    }


def cases(stem: str, after_third: bool) -> dict[str, str]:
    """The case endings a stem takes, given what stands immediately before them.

    A third-person possessive brings in the `-н-` series, which is why it is
    the one possessive the grid has to know about.
    """
    cls = final_class(stem)
    if after_third:
        return {"gen": pick("ның", "нің", stem), "dat": pick("на", "не", stem),
                "acc": pick("н", "н", stem), "loc": pick("нда", "нде", stem),
                "abl": pick("нан", "нен", stem), "ins": pick("мен", "мен", stem)}

    if cls in (FINAL_V, FINAL_N):
        gen = pick("ның", "нің", stem)
    elif cls in (FINAL_R, FINAL_Z):
        gen = pick("дың", "дің", stem)
    else:
        gen = pick("тың", "тің", stem)

    dat = pick("қа", "ке", stem) if cls == FINAL_T else pick("ға", "ге", stem)

    if cls == FINAL_V:
        acc, loc, abl = (pick("ны", "ні", stem), pick("да", "де", stem),
                         pick("дан", "ден", stem))
    elif cls in (FINAL_R, FINAL_Z, FINAL_N):
        acc, loc, abl = (pick("ды", "ді", stem), pick("да", "де", stem),
                         pick("нан", "нен", stem) if cls == FINAL_N
                         else pick("дан", "ден", stem))
    else:
        acc, loc, abl = (pick("ты", "ті", stem), pick("та", "те", stem),
                         pick("тан", "тен", stem))

    ins = {FINAL_T: "пен"}.get(cls, "бен" if stem[-1:] in "жз" else "мен")
    return {"gen": gen, "dat": dat, "acc": acc, "loc": loc, "abl": abl, "ins": ins}


# The first and second person singular possessives take a bare `-а`/`-е` in
# the dative, not `-ға`: `алмама`, `алмаңа`. Every other cell follows from the
# shape of whatever precedes it.
SHORT_DATIVE = ("1sg", "2sg")

# Predicative endings — `алмамын`, "I am an apple". They attach to the
# nominative and are what makes a Kazakh noun able to stand as a sentence.
PREDICATIVE = (("мын", "мін"), ("сың", "сің"), ("сыз", "сіз"),
               ("мыз", "міз"), ("сыңдар", "сіңдер"), ("сыздар", "сіздер"))


def paradigm(stem: str) -> list[tuple[str, str]]:
    """Every (label, form) of the number × possessive × case grid."""
    out = []
    for number, base in (("sg", stem), ("pl", stem + plural(stem))):
        for poss, ending in [("", "")] + list(possessives(base).items()):
            word = join(base, ending)
            out.append((f"{number}.{poss or '-'}.nom", word))
            grid = cases(word, after_third=(poss == "3"))
            if poss in SHORT_DATIVE:
                grid["dat"] = pick("а", "е", word)
            for case, suffix in grid.items():
                out.append((f"{number}.{poss or '-'}.{case}", join(word, suffix)))
            # The locative also derives an adjective: `алмадағы`, "the one on
            # the apple". It is regular and very common, so the grid covers it.
            out.append((f"{number}.{poss or '-'}.loc.adj",
                        join(word, grid["loc"]) + pick("ғы", "гі", word)))
        for back, front in PREDICATIVE:
            out.append((f"{number}.pred", join(base, pick(back, front, base))))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dictionaries", type=Path, nargs="*",
                    help="paths without extension, e.g. dict/kk_KZ")
    ap.add_argument("--write", type=Path, help="write the expected forms here")
    ap.add_argument("--residues", type=Path,
                    help="write the grid as residues for tools/gen_aff.py")
    ap.add_argument("--weight", type=int, default=60,
                    help="count to give paradigm residues; they are generated "
                         "from the allomorph rules, so they should outweigh a "
                         "thin corpus showing but not crush a strong one")
    args = ap.parse_args()

    grid = [(stem, label, form) for stem in STEMS for label, form in paradigm(stem)]

    if args.write:
        args.write.parent.mkdir(parents=True, exist_ok=True)
        with args.write.open("w", encoding="utf-8") as fh:
            fh.write("# stem\tcell\tform — generated by tools/paradigm.py\n")
            for stem, label, form in grid:
                fh.write(f"{stem}\t{label}\t{form}\n")
        print(f"{len(grid):,} forms over {len(STEMS)} stems → {args.write}",
              file=sys.stderr)

    if args.residues:
        from kkphon import stem_class
        from mine_residues import alternation
        rows = set()
        for stem in STEMS:
            cls = "n" + stem_class(stem)
            for _label, form in paradigm(stem):
                if form == stem:
                    continue
                strip, residue = alternation(stem, form)
                if residue:
                    rows.add((cls, strip or "0", residue))
        args.residues.parent.mkdir(parents=True, exist_ok=True)
        with args.residues.open("w", encoding="utf-8") as fh:
            fh.write("# class\tstrip\tresidue\tcount — from tools/paradigm.py\n")
            for cls, strip, residue in sorted(rows):
                fh.write(f"{cls}\t{strip}\t{residue}\t{args.weight}\n")
        print(f"{len(rows):,} paradigm residues → {args.residues}", file=sys.stderr)

    for base in args.dictionaries:
        forms = [form for _, _, form in grid]
        proc = subprocess.run(["hunspell", "-d", str(base), "-l"],
                              input="\n".join(forms), capture_output=True, text=True)
        missing = set(proc.stdout.split())
        print(f"\n{base}: {len(forms) - len(missing):,}/{len(forms):,} "
              f"({(1 - len(missing) / len(forms)) * 100:.1f}%)")
        by_stem: dict[str, list[str]] = {}
        for stem, label, form in grid:
            if form in missing:
                by_stem.setdefault(stem, []).append(f"{label}={form}")
        for stem, gaps in sorted(by_stem.items(), key=lambda kv: -len(kv[1]))[:6]:
            print(f"  {stem:<10} {len(gaps):>3} missing: {', '.join(gaps[:4])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
