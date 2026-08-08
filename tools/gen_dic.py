"""Write the wordlist with each entry's class on it.

The affix file no longer asks what a stem ends in — it is told. Every headword
carries one flag naming its vowel harmony and final segment, and that flag
selects the level-one suffix group. Classifying once here is what lets
`спорт` and `текст` inflect at all: their last vowel is three characters from
the end, out of reach of any condition the 2009 file could write.

    python tools/gen_dic.py -o dict/kk_KZ.dic

The wordlist itself is still the 2009 one, which carries inflected forms as
headwords in their own right: `абай`, `абайдан` and `абайдың` are three
separate entries. That padding was how a one-suffix affix file coped, and it is
no longer paying for itself — worse, an inflected form entered as a stem gets a
class flag of its own and lets suffixes stack on top of an already-inflected
word, which is where `*аккумуляторыдың` comes from.

`--prune` drops the ones the affix file can regenerate. Which those are is
settled by asking Hunspell rather than by reasoning about morphology: build the
dictionary without every candidate at once, and keep back whatever it then
rejects. Doing them all together is the conservative direction — a word only
goes if it survives the removal of everything else that might have explained
it — and it keeps derivations like `абайсыздық`, which are separate lexemes the
rules cannot and should not produce.
"""

from __future__ import annotations

import argparse
import collections
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from gen_aff import CLASS_FLAG  # noqa: E402
from kkphon import stem_class  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_KAZSEARCH = Path(os.environ.get("KAZSEARCH_SRC", ROOT.parent / "kazsearch-py"))

UNCAPPED = 1024


def read_wordlist(path: Path) -> list[str]:
    """Headwords, without the flags the old affix file gave them."""
    seen = {}
    for line in path.read_text(encoding="utf-8-sig").splitlines()[1:]:
        word = line.split("/")[0].split("\t")[0].strip()
        if word:
            seen.setdefault(word, None)
    return list(seen)


def entry(word: str) -> str:
    return f"{word}/{CLASS_FLAG[stem_class(word.lower())]}"


def read_pruned(path: Path) -> set[str]:
    """Headwords tools/prune.py found the affix file makes unnecessary."""
    if not path.exists():
        return set()
    return {line.strip() for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.startswith("#")}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-o", "--output", type=Path, default=ROOT / "dict/kk_KZ.dic")
    ap.add_argument("--source", type=Path, default=ROOT / "baseline/kk_KZ.dic")
    ap.add_argument("--pruned", type=Path, default=ROOT / "data/prune.txt",
                    help="headwords to drop; see tools/prune.py")
    args = ap.parse_args()

    words = read_wordlist(args.source)

    gone = read_pruned(args.pruned)
    if gone:
        words = [w for w in words if w not in gone]
        print(f"dropped {len(gone):,} headwords the affix file regenerates",
              file=sys.stderr)

    tally = collections.Counter()
    lines = []
    for word in words:
        cls = stem_class(word.lower())
        tally[cls] += 1
        lines.append(f"{word}/{CLASS_FLAG[cls]}")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(f"{len(lines)}\n" + "\n".join(sorted(lines)) + "\n",
                           encoding="utf-8")
    print(f"{len(lines):,} entries → {args.output}", file=sys.stderr)
    print("  " + "  ".join(f"{c}={n:,}" for c, n in sorted(tally.items())),
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
