"""Build Kazakh non-words that a careless affix file would accept.

Recall is trivially gamed: a dictionary that accepts every string scores 100%.
The errors an over-permissive `.aff` actually makes are not random strings
though, they are wrong *allomorphs* — a suffix attached in a shape the stem
does not license. So the negatives are made by taking real forms and swapping
one suffix for a sibling the phonology forbids.

    -лар → -лер   vowel harmony: the stem's vowels are back, the suffix is front
    -тар → -лар   voicing: -тар follows an obstruent, -лар follows a vowel

Both give strings no Kazakh text contains. Anything that does turn up in the
corpus is dropped, since the swap can land on an unrelated real word.

    python tools/negatives.py tests/corpus_cyr.txt -o tests/negatives.txt
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Suffix families: one row is the same morpheme in every shape it takes. The
# columns are (back-harmony, front-harmony) and the rows within a family differ
# only in the initial consonant the stem selects. Swapping along either axis
# produces a form the phonology rules out.
FAMILIES = [
    [("лар", "лер"), ("дар", "дер"), ("тар", "тер")],           # plural
    [("да", "де"), ("та", "те"), ("нда", "нде")],               # locative
    [("дан", "ден"), ("тан", "тен"), ("нан", "нен")],           # ablative
    [("ға", "ге"), ("қа", "ке"), ("на", "не")],                 # dative
    [("ды", "ді"), ("ты", "ті"), ("ны", "ні")],                 # accusative
    [("дың", "дің"), ("тың", "тің"), ("ның", "нің")],           # genitive
    [("мыз", "міз"), ("ңыз", "ңіз")],                           # possessive
    [("сың", "сің"), ("сыз", "сіз"), ("мын", "мін")],           # predicative
]


def swaps(word: str) -> list[str]:
    """Every one-suffix corruption of `word`, harmony and allomorph both."""
    out = []
    for family in FAMILIES:
        for row, (back, front) in enumerate(family):
            for col, form in enumerate((back, front)):
                if not word.endswith(form) or len(word) <= len(form) + 1:
                    continue
                stem = word[: -len(form)]
                for r, pair in enumerate(family):
                    for c, other in enumerate(pair):
                        if (r, c) != (row, col):
                            out.append(stem + other)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("corpus", type=Path)
    ap.add_argument("-o", "--output", type=Path, required=True)
    ap.add_argument("--limit", type=int, default=50_000,
                    help="cap the set; it is a sample, not an enumeration")
    args = ap.parse_args()

    real = set(args.corpus.read_text(encoding="utf-8").split())
    # Case matters here only to avoid a swap landing on a real capitalised form.
    real |= {w.lower() for w in real}

    seen, out = set(), []
    for word in sorted(real):
        for bad in swaps(word.lower()):
            if bad not in real and bad not in seen:
                seen.add(bad)
                out.append(bad)

    # Thin the list by taking every nth rather than the first n: the corpus is
    # alphabetical, so a prefix of it would be nothing but words starting in А.
    if len(out) > args.limit:
        out = out[:: len(out) // args.limit][: args.limit]

    args.output.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"wrote {len(out):,} non-words to {args.output}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
