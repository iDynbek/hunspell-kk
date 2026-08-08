"""Measure against running text, weighted by how often each word occurs.

Every number reported so far has come from dictionary text with each word type
counted once, and that is not what a spellchecker meets. Real text is dominated
by a small number of very common words, so a dictionary that knows the frequent
ones performs far better on a page than a type count suggests — and a rare word
it misses costs a reader one underline, not the same as missing `және`.

KazNERD is used because it is real Kazakh news prose, already tokenised, and
CC-BY-4.0. Both figures are printed: types, comparable with the rest of this
repository, and tokens, which is what a reader would actually see.

    python tools/measure_running.py --kaznerd ../KazNERD/KazNERD

@article{yeshpanov2022kaznerd,
  title={KazNERD: Kazakh Named Entity Recognition Dataset},
  author={Yeshpanov, Rustem and Khassanov, Yerbolat and Varol, Huseyin Atakan},
  journal={arXiv preprint arXiv:2111.13419}, year={2021}}
"""

from __future__ import annotations

import argparse
import collections
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_KAZNERD = ROOT.parent / "KazNERD/KazNERD"

CYRILLIC_WORD = re.compile(r"^[Ѐ-ӿ]+$")


def tokens(directory: Path, split: str = "*") -> collections.Counter:
    """Every Cyrillic token in the IOB2 files, with its count.

    The format is one `token TAG` per line and a blank line between sentences,
    so the first field is the word. Counts are kept because they are the whole
    point: `және` appearing 40,000 times should weigh 40,000 times as much as a
    word appearing once.
    """
    counts = collections.Counter()
    for path in sorted(directory.glob(f"IOB2_{split}.txt")):
        for line in path.read_text(encoding="utf-8").splitlines():
            word = line.split(" ")[0].strip()
            if CYRILLIC_WORD.match(word):
                counts[word] += 1
    return counts


def rejected(base: Path, words: list[str]) -> set[str]:
    proc = subprocess.run(["hunspell", "-d", str(base), "-l"],
                          input="\n".join(words), capture_output=True, text=True)
    if proc.returncode != 0:
        sys.exit(f"hunspell failed: {proc.stderr.strip()}")
    return set(proc.stdout.split())


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dictionaries", type=Path, nargs="+",
                    help="paths without extension, e.g. dict/kk_KZ baseline/kk_KZ")
    ap.add_argument("--kaznerd", type=Path, default=DEFAULT_KAZNERD)
    ap.add_argument("--split", default="*",
                    help="which IOB2 files to measure: test, valid, train, or * "
                         "for all. Anything mined from KazNERD must be mined "
                         "from train and measured on test, or the number is a "
                         "memory test.")
    ap.add_argument("--show-misses", type=int, default=0,
                    help="print this many of the most frequent rejected words")
    args = ap.parse_args()

    if not args.kaznerd.exists():
        sys.exit(f"no KazNERD at {args.kaznerd} — clone IS2AI/KazNERD")

    counts = tokens(args.kaznerd, args.split)
    types = sorted(counts)
    total = sum(counts.values())
    print(f"{total:,} Cyrillic tokens, {len(types):,} distinct\n")

    for base in args.dictionaries:
        misses = rejected(base, types)
        flagged = sum(counts[w] for w in misses)
        print(f"{base}")
        print(f"  by token  {(1 - flagged / total) * 100:5.1f}% accepted"
              f"   {flagged:>9,} of {total:,} flagged")
        print(f"  by type   {(1 - len(misses) / len(types)) * 100:5.1f}% accepted"
              f"   {len(misses):>9,} of {len(types):,} flagged")
        if args.show_misses:
            worst = sorted(misses, key=lambda w: -counts[w])[:args.show_misses]
            print("  most costly rejections: "
                  + ", ".join(f"{w} ({counts[w]:,})" for w in worst))
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
