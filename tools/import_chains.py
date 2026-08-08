"""Take the suffix chains KazNLP's analyzer knows about.

The affix file learns its chains from the corpus, which means a legal one that
nobody happened to write is not in it. Composing from morpheme adjacency
recovers many, but only where the corpus attested both halves of the join.

[KazNLP](https://github.com/nlacslab/kaznlp) ships a suffix inventory that is
already unfolded — 1,165 strings, each tagged with the analysis it stands for,
up to five morphemes deep:

    деріміз       N1-S5           plural, first person plural possessive
    дерімізді     N1-S5-C4        and accusative
    тылуына       V4-V2-ET_ETU-S3-C3

That is the same unfolding this repository does, arrived at independently and
from a treebank rather than from running text, so it covers chains the corpus
does not. Only the strings are taken; the analyses come along because they say
how many morphemes a string holds, which is worth keeping for later.

    python tools/import_chains.py -o data/chains.tsv
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SFX = ROOT.parent / "kaznlp/kaznlp/morphology/mdl/sfx"

CYRILLIC = re.compile(r"^[Ѐ-ӿ]+$")


def read_sfx(path: Path) -> list[tuple[str, str]]:
    """(suffix string, analysis), with the leading hyphen the file marks bound
    morphemes with removed."""
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        suffix, _, analysis = line.partition("\t")
        suffix = suffix.lstrip("-").strip()
        if suffix and CYRILLIC.match(suffix):
            out.setdefault(suffix, analysis.strip())
    return sorted(out.items())


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-o", "--output", type=Path, default=ROOT / "data/chains.tsv")
    ap.add_argument("--sfx", type=Path, default=DEFAULT_SFX)
    args = ap.parse_args()

    if not args.sfx.exists():
        sys.exit(f"no KazNLP suffix table at {args.sfx} — pass --sfx")

    rows = read_sfx(args.sfx)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as fh:
        fh.write("# suffix\tanalysis — from KazNLP, via tools/import_chains.py\n")
        for suffix, analysis in rows:
            fh.write(f"{suffix}\t{analysis}\n")
    print(f"{len(rows):,} chains → {args.output}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
