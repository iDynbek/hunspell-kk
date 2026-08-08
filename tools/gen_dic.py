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
from kkphon import TRACKS, stem_class  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

UNKNOWN = "n"


def read_lexicon(path: Path) -> dict[str, str]:
    """word → the tracks it inflects on, `nv` where nothing decides."""
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line and not line.startswith("#"):
            word, tracks, _sources = line.split("\t")
            out[word] = tracks if tracks in ("n", "v", "nv") else UNKNOWN
    return out


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


def entry(word: str, tracks: str = "nv") -> str:
    phon = stem_class(word.lower())
    flags = [str(CLASS_FLAG[t + phon]) for t in tracks]
    if word.lower() in ELIDES:
        flags.append(str(ELIDE_FLAG))
    return f"{word}/{','.join(flags)}"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-o", "--output", type=Path, default=ROOT / "dict/kk_KZ.dic")
    ap.add_argument("--lexicon", type=Path, default=ROOT / "data/lexicon.tsv")
    ap.add_argument("--elide", type=Path, default=ROOT / "data/elide.txt")
    ap.add_argument("--pruned", type=Path, default=ROOT / "data/prune.txt",
                    help="headwords to drop; see tools/prune.py")
    args = ap.parse_args()

    ELIDES.update(read_elide(args.elide))
    lexicon = read_lexicon(args.lexicon)

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

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(f"{len(lines)}\n" + "\n".join(sorted(lines)) + "\n",
                           encoding="utf-8")
    print(f"{len(lines):,} entries → {args.output}", file=sys.stderr)
    print("  " + "  ".join(f"{k}={v:,}" for k, v in sorted(tally.items())),
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
