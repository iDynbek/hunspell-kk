"""Take proper names from KazNERD's entity annotations.

Two fifths of everything the dictionary flags in running text is a proper name
— `Тоқаев`, `Назарбаевтың`, `Түркістаннан`. Names are not a morphology problem
and not really a vocabulary problem either; they are their own list, which is
how most Hunspell dictionaries treat them. KazNERD has already marked them.

Names arrive inflected, so they are lemmatised: of the stems the ladder offers,
the longest one that KazNERD itself also uses as a bare name is taken. That
avoids over-stripping `Түркістан` down to something shorter that happens to be
reachable, and it needs no judgement about Kazakh onomastics.

**Only the training split is read.** KazNERD is also what
`tools/measure_running.py` measures against, and mining names from the same
text one is scored on turns the score into a memory test. Mine from train,
measure on test.

    python tools/mine_names.py -o data/names.txt

KazNERD is CC-BY-4.0:
  Yeshpanov, R., Khassanov, Y., Varol, H.A. KazNERD: Kazakh Named Entity
  Recognition Dataset. arXiv:2111.13419, 2021.
"""

from __future__ import annotations

import argparse
import collections
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_KAZNERD = ROOT.parent / "KazNERD/KazNERD"
DEFAULT_KAZSEARCH = Path(os.environ.get("KAZSEARCH_SRC", ROOT.parent / "kazsearch-py"))

CYRILLIC_WORD = re.compile(r"^[Ѐ-ӿ]+$")
UNCAPPED = 1024

# Entity types that are names. The rest of KazNERD's inventory marks numbers,
# dates, money and quantities, which are not wordlist material.
NAME_TAGS = frozenset({
    "PERSON", "GPE", "LOCATION", "ORGANISATION", "FACILITY", "NORP",
    "PRODUCT", "PROJECT", "EVENT", "ART", "LAW", "LANGUAGE",
})


def name_tokens(directory: Path, split: str) -> collections.Counter:
    counts = collections.Counter()
    for path in sorted(directory.glob(f"IOB2_{split}.txt")):
        for line in path.read_text(encoding="utf-8").splitlines():
            parts = line.split(" ")
            if len(parts) < 2:
                continue
            word, tag = parts[0].strip(), parts[1].strip()
            # Only capitalised tokens. Entity spans routinely swallow ordinary
            # words — `Қамтамасыз ету министрлігі` puts `ету` and `министрлігі`
            # inside an ORGANISATION — and those are vocabulary, not names.
            if (tag[2:] in NAME_TAGS and CYRILLIC_WORD.match(word)
                    and len(word) > 2 and word[0].isupper()):
                counts[word] += 1
    return counts


# Case endings long and distinctive enough that they cannot be the tail of a
# root. The short ones are deliberately left out: `-ты` is an accusative but
# also the end of `Алматы`, `-с` plus `-тан` would take `Қазақстан` down to
# `Қазақ`. Leaving an inflected name unreduced costs one redundant entry;
# reducing a real name to a fragment invents a word.
NAME_ENDINGS = frozenset((
    "ның", "нің", "дың", "дің", "тың", "тің",          # genitive
    "дан", "ден", "тан", "тен", "нан", "нен",          # ablative
    "нда", "нде", "ында", "інде",                      # locative after possessive
    "мен", "бен", "пен",                               # instrumental
    "лар", "лер", "дар", "дер", "тар", "тер",          # plural
    "ына", "іне", "ынан", "інен", "ының", "інің",      # possessive plus case
))


def removable(tail: str) -> bool:
    """One ending, or two of them stacked — nothing else comes off a name."""
    if tail in NAME_ENDINGS:
        return True
    return any(tail[:k] in NAME_ENDINGS and tail[k:] in NAME_ENDINGS
               for k in range(1, len(tail)))


def lemmatise(counts: collections.Counter, segmentable) -> dict[str, int]:
    """Inflected name forms → the base form, by agreement with the corpus.

    The ladder is no use here: it is built for Kazakh stems and cannot take
    `-тың` off `Абаевтың`, because Russian-style surnames in -ов/-ев are not in
    its model. But Kazakh suffixes are strictly suffixal, so the base of a name
    is simply the longest proper prefix of it that KazNERD also uses as a name
    on its own — `Қазақстаннан` over `Қазақстан`, `Абаевтың` over `Абаев`.

    The remainder has to be one of a short list of unmistakable case endings.
    Anything more permissive over-strips: `-с` and `-тан` are both morphemes,
    so general segmentability takes `Қазақстан` down to `Қазақ`.
    """
    bare = {w.lower() for w in counts if len(w) > 2}

    def reduce_once(word: str) -> str | None:
        for cut in range(len(word) - 1, 2, -1):
            if word[:cut] in bare and removable(word[cut:]):
                return word[:cut]
        return None

    lemmas = collections.Counter()
    for word, n in counts.items():
        best = word.lower()
        # One pass takes `Абайдағы` only as far as `Абайда`, which is itself an
        # attested form; repeating until nothing more comes off reaches `Абай`.
        while (shorter := reduce_once(best)) is not None:
            best = shorter
        lemmas[best] += n
    return lemmas


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-o", "--output", type=Path, default=ROOT / "data/names.txt")
    ap.add_argument("--kaznerd", type=Path, default=DEFAULT_KAZNERD)
    ap.add_argument("--kazsearch", type=Path, default=DEFAULT_KAZSEARCH)
    ap.add_argument("--split", default="train",
                    help="never set this to a split you also measure on")
    ap.add_argument("--min-count", type=int, default=2,
                    help="a name seen once is as likely to be a typo as a name")
    args = ap.parse_args()

    if not args.kaznerd.exists():
        sys.exit(f"no KazNERD at {args.kaznerd} — clone IS2AI/KazNERD")
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from gen_aff import _segmentable, morphemes  # noqa: E402
    inventory = morphemes(args.kazsearch)

    counts = name_tokens(args.kaznerd, args.split)
    lemmas = lemmatise(counts, lambda s: _segmentable(s, inventory))
    kept = sorted(w for w, n in lemmas.items() if n >= args.min_count)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        f"# proper names from KazNERD {args.split} (CC-BY-4.0), "
        "via tools/mine_names.py\n" + "\n".join(kept) + "\n", encoding="utf-8")
    print(f"{sum(counts.values()):,} name tokens, {len(counts):,} forms → "
          f"{len(lemmas):,} lemmas, {len(kept):,} kept → {args.output}",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
