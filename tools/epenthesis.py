"""Add the consonant-cluster loanword forms Apertium validates.

Loanwords ending in a consonant cluster — `акт`, `факт`, `пункт`, `туризм`,
`объект` — inflect irregularly. Most insert an epenthetic vowel before a
suffix (`акт` → `актіге`, `актісі`), but which vowel, whether it appears at
all, and its harmony vary per lexeme and even per case: `актіге` but `актқа`,
`спортқа` (back, none), `банкке` (front, none), `туризмі` (only in the
possessive). No affix class captures this, and hand-writing it injects wrong
forms — `актты`, `спортыға`, `банкіге` are all things a rule would produce and
none are Kazakh.

So the forms are generated and then judged by apertium-kaz, which distinguishes
a valid spelling from one it merely recognises in order to correct: `актісі`
gets a clean analysis, `актты` only an `err_orth` one. Only the clean ones are
kept, and listed outright in the dictionary rather than generated.

    python tools/epenthesis.py -o data/epenthesis.txt

Needs the analyzer in the `apertium` distrobox (see tools/audit_apertium.py).
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from gen_dic import read_lexicon  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

LOOKUP = "hfst-lookup -q /usr/share/apertium/apertium-kaz/kaz.automorf.hfst"

CONSONANTS = set("бвгғджзйкқлмнңпрстфхһцчшщ")
# Cluster endings that trigger the irregular loanword inflection.
TRIGGERS = ("кт", "нкт", "нк", "рк", "рт", "пт", "фт", "ск", "ст",
            "зм", "нг", "рг", "бт", "кс", "пс", "нс", "мп", "нт")

# The three patterns a cluster loanword might follow; Apertium sorts out which
# forms of which are real per stem.
EPENTHETIC = ("іге", "іде", "іден", "інің", "іні", "ісі", "ілер", "ілердің",
              "ілерге", "інде", "інен", "імен", "інде")
FRONT = ("ке", "те", "де", "тен", "нің", "ні", "ті", "сі", "лер", "мен", "пен")
BACK = ("қа", "та", "да", "тан", "ның", "ны", "ты", "сы", "лар", "мен", "пен")


def analyze(words: list[str]) -> dict[str, list[str]]:
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".txt",
                                     dir=Path.home(), delete=False) as fh:
        fh.write("\n".join(words))
        path = fh.name
    try:
        proc = subprocess.run(
            ["distrobox", "enter", "apertium", "--", "bash", "-c",
             f"{LOOKUP} < {path}"],
            capture_output=True, text=True, timeout=580)
    finally:
        Path(path).unlink(missing_ok=True)
    out: dict[str, list[str]] = {}
    for line in proc.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) >= 3:
            out.setdefault(parts[0], []).append(parts[1])
    return out


def clean(analyses: list[str]) -> bool:
    """True if a non-error analysis exists — Apertium calls it a real spelling."""
    return any(not a.endswith("+?") and "err" not in a for a in analyses)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-o", "--output", type=Path, default=ROOT / "data/epenthesis.txt")
    ap.add_argument("--lexicon", type=Path, default=ROOT / "data/lexicon.tsv")
    args = ap.parse_args()

    lexicon = read_lexicon(args.lexicon)
    stems = sorted(w for w in lexicon if len(w) >= 3 and w.endswith(TRIGGERS)
                   and w[-1] in CONSONANTS and w[-2] in CONSONANTS)
    candidates = sorted({stem + suf for stem in stems
                         for suf in EPENTHETIC + FRONT + BACK})
    print(f"{len(stems):,} cluster stems, {len(candidates):,} candidate forms",
          file=sys.stderr)

    analyses = analyze(candidates)
    valid = sorted(w for w in candidates if clean(analyses.get(w, [])))

    from gen_dic import read_lexicon as _rl  # noqa: F401
    proc = subprocess.run(
        ["hunspell", "-d", str(ROOT / "dict/kk_KZ"), "-l"],
        input="\n".join(valid), capture_output=True, text=True)
    new = sorted(set(proc.stdout.split()))

    args.output.write_text(
        "# consonant-cluster loanword forms apertium-kaz validates with a clean\n"
        "# (non-error) analysis and this dictionary lacked; tools/epenthesis.py\n"
        + "\n".join(new) + "\n", encoding="utf-8")
    print(f"{len(valid):,} valid, {len(new):,} new → {args.output}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
