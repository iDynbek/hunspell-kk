"""Write the wordlist with each entry's class on it.

The affix file no longer asks what a stem ends in or what part of speech it is —
it is told. Every headword carries a flag naming its track, its vowel harmony
and its final segment, and that flag selects the level-one suffix group.

Classifying once here is what lets `спорт` and `текст` inflect at all: their
last vowel is three characters from the end, out of reach of any condition the
2009 file could write. And carrying the track is what keeps `-дың` — genitive on
a noun, second-person past on a verb — off `адам`.

A word that is both noun and verb, like `бала`, gets both flags: it really does
inflect both ways. A word no source gives a part of speech gets both as well,
which is no worse than the single undivided class it had before.

    python tools/gen_dic.py -o dict/kk_KZ.dic
"""

from __future__ import annotations

import argparse
import collections
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from gen_aff import CLASS_FLAG, ELIDE_FLAG  # noqa: E402
from kkphon import TRACKS, final_class, harmony, stem_class  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

UNKNOWN = "n"


def read_lexicon(path: Path, without: frozenset = frozenset()) -> dict[str, str]:
    """word → the tracks it inflects on, `nv` where nothing decides.

    `without` drops entries vouched for *only* by the named sources. The
    kazdict rows carry an uncleared database-rights question, and upstreams
    ask; a build without them loses 0.8 points of token coverage and answers
    the question by not raising it.
    """
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line and not line.startswith("#"):
            word, tracks, _sources = line.split("\t")
            if without and not (set(_sources.split(",")) - without):
                continue
            out[word] = tracks if tracks in ("n", "v", "nv") else UNKNOWN
    return out


def read_extra_forms(path: Path) -> list[str]:
    """Fully-inflected forms added as their own entries, no affix flag.

    The consonant-cluster loanwords — `акт`, `туризм`, `объект` — take an
    epenthetic vowel whose presence, harmony and scope vary per lexeme
    (`актіге` but `спортқа`, `банкке` but `туризмі`), too irregular for a class.
    Each form here was generated and then validated by apertium-kaz with a
    clean, non-error analysis, so they are listed outright rather than
    generated. See the epenthesis audit.
    """
    if not path.exists():
        return []
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.startswith("#")]


def read_pruned(path: Path) -> set[str]:
    """Headwords tools/prune.py found the affix file makes unnecessary."""
    if not path.exists():
        return set()
    return {line.strip() for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.startswith("#")}


def read_elide(path: Path) -> set[str]:
    """Stems observed to drop their last vowel; see tools/mine_residues.py."""
    if not path.exists():
        return set()
    return {line.strip() for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.startswith("#")}


ELIDES: set[str] = set()
OPENERS: set[str] = set()


def read_openers(path: Path) -> set[str]:
    """Elements that may open a compound; see tools/mine_compounds.py."""
    if not path.exists():
        return set()
    return {line.strip() for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.startswith("#")}

# Stems whose harmony the corpus contradicts; see tools/mine_harmony.py.
HARMONY: dict[str, str] = {}


def read_harmony(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line and not line.startswith("#"):
            stem, value = line.split("\t")
            out[stem] = value
    return out


def entry(word: str, tracks: str = "nv") -> str:
    low = word.lower()
    # `банк` takes `банктен` and `конференция` takes `конференцияда`: a
    # loanword's harmony is a fact about the word, not about its vowels.
    phon = (HARMONY[low] + final_class(low)) if low in HARMONY else stem_class(low)
    flags = [str(CLASS_FLAG[t + phon]) for t in tracks]
    if low in ELIDES:
        flags.append(str(ELIDE_FLAG))
    # Compound flags are not emitted; see NOTES.md for the measurement.
    return f"{word}/{','.join(flags)}"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-o", "--output", type=Path, default=ROOT / "dict/kk_KZ.dic")
    ap.add_argument("--lexicon", type=Path, default=ROOT / "data/lexicon.tsv")
    ap.add_argument("--elide", type=Path, default=ROOT / "data/elide.txt")
    ap.add_argument("--harmony", type=Path, default=ROOT / "data/harmony.tsv")
    ap.add_argument("--compounds", type=Path, default=ROOT / "data/compounds.txt")
    ap.add_argument("--epenthesis", type=Path, default=ROOT / "data/epenthesis.txt")
    ap.add_argument("--extra", type=Path, default=ROOT / "data/extra_forms.txt")
    ap.add_argument("--without", default="",
                    help="comma-separated sources; drop entries only they vouch for")
    ap.add_argument("--pruned", type=Path, default=ROOT / "data/prune.txt",
                    help="headwords to drop; see tools/prune.py")
    args = ap.parse_args()

    ELIDES.update(read_elide(args.elide))
    HARMONY.update(read_harmony(args.harmony))
    OPENERS.update(read_openers(args.compounds))
    lexicon = read_lexicon(args.lexicon,
                           frozenset(s for s in args.without.split(",") if s))

    gone = {w.lower() for w in read_pruned(args.pruned)}
    if gone:
        lexicon = {w: t for w, t in lexicon.items() if w not in gone}
        print(f"dropped {len(gone):,} headwords the affix file regenerates",
              file=sys.stderr)

    tally = collections.Counter()
    lines = []
    for word, tracks in lexicon.items():
        tally[tracks] += 1
        lines.append(entry(word, tracks))

    extra = read_extra_forms(args.epenthesis) + read_extra_forms(args.extra)
    lines.extend(extra)
    if extra:
        print(f"added {len(extra):,} Apertium-validated forms", file=sys.stderr)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(f"{len(lines)}\n" + "\n".join(sorted(set(lines))) + "\n",
                           encoding="utf-8")
    print(f"{len(lines):,} entries → {args.output}", file=sys.stderr)
    print("  " + "  ".join(f"{k}={v:,}" for k, v in sorted(tally.items())),
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
