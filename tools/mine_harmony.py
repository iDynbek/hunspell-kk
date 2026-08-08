"""Find the stems whose harmony cannot be read off their vowels.

`kkphon.harmony()` takes the harmony from the last vowel that commits to one,
which is right for native Kazakh and wrong for a great many loanwords. `банк`
has a back vowel and takes `банктен`; `министр`, `фильм`, `турист` and
`брифинг` all take front endings; `конференция` and `инфекция` go the other
way and take back ones despite their front vowels. Kazakh assigns loans the
harmony it assigns them, and no rule over the letters recovers it.

So it is taken from the corpus instead. Where a stem's attested suffixes carry
one harmony and the classifier says the other, the corpus wins and the stem
gets an override, exactly as eliding stems get one.

    python tools/mine_harmony.py -o data/harmony.tsv

Evidence has to be more than incidental, because the corpus contains typos and
the stemmer misanalyses: a stem needs several tokens and a clear majority
before its computed harmony is overruled.
"""

from __future__ import annotations

import argparse
import collections
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from kkphon import HARM_BACK, HARM_FRONT, harmony  # noqa: E402
from mine_residues import alternation, candidate_stems  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_KAZSEARCH = Path(os.environ.get("KAZSEARCH_SRC", ROOT.parent / "kazsearch-py"))

# Vowels that commit a *suffix* to one harmony. A suffix carrying none of them
# — `-мен`, `-н` — says nothing about the stem.
BACK_SUFFIX_VOWELS = frozenset("аоұы")
FRONT_SUFFIX_VOWELS = frozenset("әеөүі")


def inflectional(kazsearch: Path) -> frozenset[str]:
    """The case, plural, possessive and predicative endings — no derivation.

    Harmony evidence has to come from these and nothing else. A derivational
    suffix carries its own harmony: `талапкер` (applicant) is `талап` plus the
    front `-кер`, and counting its front vowel made `талап` — a plainly back
    word, `талапқа`, `талапты` — come out front, and every plural of one of the
    commonest words in a legal text was then rejected.
    """
    sys.path.insert(0, str(kazsearch / "src"))
    from kazsearch import rules as R
    return frozenset(r.suffix for table in
                     ("CASE_RULES", "PLUR_RULES", "POSS_RULES", "PRED_RULES")
                     for r in getattr(R, table))


def suffix_harmony(residue: str, endings: frozenset[str]) -> str | None:
    """The harmony a residue commits its stem to, or None.

    Only a residue that is exactly one inflectional ending counts. `қа` and
    `ке` do; `керге` does not, even though it opens with the dative `ке` —
    a derivation is not evidence about the base, and a multi-suffix form can
    hide one past the first morpheme.
    """
    if residue not in endings:
        return None
    vowels = set(residue)
    if vowels & FRONT_SUFFIX_VOWELS:
        return HARM_FRONT
    if vowels & BACK_SUFFIX_VOWELS:
        return HARM_BACK
    return None


def blind_split(word: str, stems: set[str], suffixes: set[str]) -> str | None:
    """Split without consulting harmony at all.

    The ladder will not take `-тен` off `банктен`, because its own model says
    `банк` is back and a back stem does not wear a front suffix — the very
    error being looked for. Asking it therefore finds evidence everywhere
    except where it is needed. Matching a known suffix string against a known
    stem has no opinion about harmony and finds them.
    """
    for cut in range(len(word) - 1, 2, -1):
        if word[:cut] in stems and word[cut:] in suffixes:
            return word[:cut]
    return None


def gather(corpus: collections.Counter, stems: set[str], ladder,
           endings: frozenset[str], suffixes: set[str] = frozenset()
           ) -> dict[str, collections.Counter]:
    """Per stem, how many tokens wore front endings and how many wore back.

    Weighted by frequency, since a loanword's harmony is settled by how it is
    actually inflected and one stray form should not outvote a hundred.
    """
    evidence: dict[str, collections.Counter] = collections.defaultdict(
        collections.Counter)
    for word, weight in corpus.items():
        low = word.lower()
        stem = None
        for rung in candidate_stems(low, ladder):
            if rung in stems and (stem is None or len(rung) < len(stem)):
                stem = rung
        if stem is None or stem == low:
            stem = blind_split(low, stems, suffixes)
        if stem is None or stem == low:
            continue
        _strip, residue = alternation(stem, low)
        if not residue:
            continue
        wears = suffix_harmony(residue, endings)
        if wears:
            evidence[stem][wears] += weight
    return evidence


def overrides(evidence, min_tokens: int, majority: float) -> dict[str, str]:
    out = {}
    for stem, counts in evidence.items():
        total = sum(counts.values())
        if total < min_tokens:
            continue
        wears, seen = counts.most_common(1)[0]
        if seen / total >= majority and wears != harmony(stem):
            out[stem] = wears
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-o", "--output", type=Path, default=ROOT / "data/harmony.tsv")
    ap.add_argument("--corpus", type=Path, default=ROOT / "tests/corpus_cyr.txt")
    ap.add_argument("--kaznerd", type=Path, default=ROOT.parent / "KazNERD/KazNERD",
                    help="training split only: this is also the evaluation corpus")
    ap.add_argument("--lexicon", type=Path, default=ROOT / "data/lexicon.tsv")
    ap.add_argument("--kazsearch", type=Path, default=DEFAULT_KAZSEARCH)
    ap.add_argument("--min-tokens", type=int, default=4)
    ap.add_argument("--majority", type=float, default=0.8)
    args = ap.parse_args()

    if not args.corpus.exists():
        sys.exit(f"no corpus at {args.corpus} — run `make baseline` first")
    sys.path.insert(0, str(args.kazsearch / "src"))
    try:
        from kazsearch.ladder import ladder
    except ImportError:
        sys.exit(f"no kazsearch under {args.kazsearch} — pass --kazsearch")

    stems = {line.split("\t")[0]
             for line in args.lexicon.read_text(encoding="utf-8").splitlines()
             if line and not line.startswith("#")}
    words = collections.Counter(args.corpus.read_text(encoding="utf-8").split())
    # Dictionary prose rarely inflects a loanword; news prose does nothing else.
    # `банк`, `карантин` and `брифинг` have no evidence at all without this.
    if args.kaznerd.exists():
        from measure_running import tokens
        for word, n in tokens(args.kaznerd, "train").items():
            words[word] += min(n, 20)          # cap: one frequent word, one vote
        print("  plus KazNERD train", file=sys.stderr)
    suffixes = {line.split("\t")[2]
                for line in (ROOT / "data/residues.tsv").read_text(
                    encoding="utf-8").splitlines()
                if line and not line.startswith("#")}
    endings = inflectional(args.kazsearch)
    evidence = gather(words, stems, ladder, endings, suffixes)
    found = overrides(evidence, args.min_tokens, args.majority)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as fh:
        fh.write("# stem\tharmony — the corpus disagreeing with kkphon.harmony(),\n"
                 "# generated by tools/mine_harmony.py\n")
        for stem in sorted(found):
            fh.write(f"{stem}\t{found[stem]}\n")

    tally = collections.Counter(found.values())
    print(f"{len(evidence):,} stems with harmony evidence, {len(found):,} overruled "
          f"→ {args.output}", file=sys.stderr)
    print("  " + "  ".join(f"to {k}={v:,}" for k, v in sorted(tally.items())),
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
