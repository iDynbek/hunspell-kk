"""Write the wordlist with each entry's class on it.

The affix file no longer asks what a stem ends in — it is told. Every headword
carries one flag naming its vowel harmony and final segment, and that flag
selects the level-one suffix group. Classifying once here is what lets
`спорт` and `текст` inflect at all: their last vowel is three characters from
the end, out of reach of any condition the 2009 file could write.

    python tools/gen_dic.py -o dict/kk_KZ.dic

The wordlist itself is still the 2009 one. It carries inflected forms as
headwords in their own right — `абай`, `абайдан` and `абайдың` are three
separate entries — and de-inflating those is separate work; entering a form
twice costs a little size and no correctness.
"""

from __future__ import annotations

import argparse
import collections
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from gen_aff import CLASS_FLAG  # noqa: E402
from kkphon import stem_class  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def read_wordlist(path: Path) -> list[str]:
    """Headwords, without the flags the old affix file gave them."""
    seen = {}
    for line in path.read_text(encoding="utf-8-sig").splitlines()[1:]:
        word = line.split("/")[0].split("\t")[0].strip()
        if word:
            seen.setdefault(word, None)
    return list(seen)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-o", "--output", type=Path, default=ROOT / "dict/kk_KZ.dic")
    ap.add_argument("--source", type=Path, default=ROOT / "baseline/kk_KZ.dic")
    args = ap.parse_args()

    words = read_wordlist(args.source)
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
