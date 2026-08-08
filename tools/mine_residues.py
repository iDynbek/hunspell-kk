"""Collect the suffix strings Kazakh text actually puts on a stem.

The alternative is enumerating the layer model's cross-product, and it does not
survive contact with the arithmetic: the nominal chain alone is 45 × 6 × 24 ×
40 × 16 combinations, almost all of which no Kazakh speaker has ever uttered.
Mining instead gives a set that is both smaller and better targeted — 4,300
residues, of which the top 800 account for 92% of analysable forms.

Each residue is recorded against the *class* of stem it was seen on, because
that is what picks the suffix's shape: `-тар` after `мектеп`, `-дар` after
`жол`, `-лар` after `бала`. Taking the pairing from the corpus rather than
hand-writing an allomorph table is what keeps the 2009 file's half-typed
consonant lists from being reintroduced.

    python tools/mine_residues.py -o data/residues.tsv

The output is committed so that generating the affix file needs only this
repository; regenerating it needs a corpus and a checkout of kazsearch-py.
"""

from __future__ import annotations

import argparse
import collections
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from kkphon import (EXTRA_MORPHEMES, TRACKS, VOWELS, stem_class,  # noqa: E402
                    takes_bare_suffix)

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_KAZSEARCH = Path(os.environ.get("KAZSEARCH_SRC", ROOT.parent / "kazsearch-py"))

UNCAPPED = 1024


def single_track(lexicon: Path) -> dict[str, str]:
    """Words with exactly one part of speech, mapped to its track."""
    out = {}
    for line in lexicon.read_text(encoding="utf-8").splitlines():
        if line and not line.startswith("#"):
            word, tracks, _sources = line.split("\t")
            if len(tracks) == 1 and tracks in TRACKS:
                out[word] = tracks
    return out


# A stem-final voiceless stop voices before a vowel-initial suffix: `кітап` is
# `кітабы`, `бақ` is `бағы`, `жүрек` is `жүрегі`. 2,824 corpus forms do this.
VOICING = {"қ": "ғ", "к": "г", "п": "б"}

# Only the high vowels elide, and only in the last syllable of a stem.
ELIDING_VOWELS = frozenset("ыіұү")


def candidate_stems(word: str, ladder) -> list[str]:
    """Every stem the word might rest on, the ladder's answers plus one more.

    The layer model has `-ып` but not the `-п` it becomes after a vowel, so the
    ladder stops one rung short on `құлап`, `ізде+п`, `оқы+т`. Stripping a bare
    suffix is only allowed where it leaves a vowel-final stem, which is the
    condition under which those forms exist at all, and the caller still has to
    find the result in the lexicon — so a wrong strip goes nowhere.
    """
    rungs = ladder(word, max_rungs=UNCAPPED)
    extra = []
    for rung in rungs:
        if len(rung) > 2 and rung[-1] in EXTRA_MORPHEMES:
            shorter = rung[:-1]
            if takes_bare_suffix(shorter):
                extra.append(shorter)
                extra.extend(ladder(shorter, max_rungs=UNCAPPED))
    return rungs + extra


def alternation(stem: str, form: str) -> tuple[str, str | None]:
    """What the suffix is, and what it costs the stem to take it.

    Slicing the form at the stem's length is wrong wherever the stem changes
    shape: it reads `кітабы` as `кітап` + `ы`, which generates `*кітапы` and
    never `кітабы`. Returning the strip separately lets the rule be written as
    Hunspell wants it — take `п` off, put `бы` on.

    A stem can also drop its last vowel: `орын` is `орны`, `мойын` is `мойны`.
    That is written as a strip too — take `ын` off `мойын`, put `нын` on — but
    it cannot be applied by shape, because `қатын` keeps its vowel and the rule
    would make it `*қатнын`. Which stems elide is lexical, so they are collected
    and flagged individually.
    """
    if form.startswith(stem):
        return "", form[len(stem):]
    voiced = VOICING.get(stem[-1:])
    if voiced and form.startswith(stem[:-1] + voiced):
        return stem[-1], form[len(stem):]
    elided = elision(stem, form)
    if elided:
        return elided
    return "", None


def elision(stem: str, form: str) -> tuple[str, str] | None:
    """`мойын` + `ын` → `мойнын`: drop the stem's last vowel, keep what follows."""
    if len(stem) < 3 or stem[-1] in VOWELS or stem[-2] not in ELIDING_VOWELS:
        return None
    shortened = stem[:-2] + stem[-1]
    if not form.startswith(shortened) or len(form) <= len(shortened):
        return None
    return stem[-2:], stem[-1] + form[len(shortened):]


def mine(corpus: list[str], tracks: dict[str, str], ladder) -> collections.Counter:
    """(stem class, residue) → how many corpus forms it explains.

    The *shortest* headword on the ladder wins, so a form is charged to the
    longest suffix string that reaches a known stem. Taking the longest
    headword instead would credit `мектептер` to `мектептер` whenever that had
    been entered as a headword in its own right, and the 2009 wordlist is full
    of those — which is precisely the padding this is meant to see past.

    Only stems with one part of speech contribute. A word that is both noun and
    verb cannot say which of its two tracks a suffix belongs to, and counting it
    for both would put every verbal ending back on the nominal track — undoing
    the split the tracks exist for. Such words still inflect both ways; they
    just do not get a vote on what either track contains.
    """
    counts, elides = collections.Counter(), set()
    for word in corpus:
        low = word.lower()
        stem = None
        for rung in candidate_stems(low, ladder):
            if rung in tracks and (stem is None or len(rung) < len(stem)):
                stem = rung
        if stem is None or stem == low:
            continue
        strip, residue = alternation(stem, low)
        if residue is None:
            continue
        if len(strip) > 1:
            elides.add(stem)
        counts[tracks[stem] + stem_class(stem), strip, residue] += 1
    return counts, elides


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-o", "--output", type=Path, default=ROOT / "data/residues.tsv")
    ap.add_argument("--corpus", type=Path, default=ROOT / "tests/corpus_cyr.txt")
    ap.add_argument("--lexicon", type=Path, default=ROOT / "data/lexicon.tsv")
    ap.add_argument("--elide", type=Path, default=ROOT / "data/elide.txt")
    ap.add_argument("--kazsearch", type=Path, default=DEFAULT_KAZSEARCH)
    ap.add_argument("--min-count", type=int, default=2,
                    help="drop residues seen once; at that frequency a stemmer "
                         "misanalysis is as likely as a real suffix")
    args = ap.parse_args()

    if not args.corpus.exists():
        sys.exit(f"no corpus at {args.corpus} — run `make baseline` first")
    sys.path.insert(0, str(args.kazsearch / "src"))
    try:
        from kazsearch.ladder import ladder
    except ImportError:
        sys.exit(f"no kazsearch under {args.kazsearch} — pass --kazsearch")

    counts, elides = mine(args.corpus.read_text(encoding="utf-8").split(),
                          single_track(args.lexicon), ladder)
    args.elide.write_text("# stems that drop their last vowel, from "
                          "tools/mine_residues.py\n" + "\n".join(sorted(elides))
                          + "\n", encoding="utf-8")
    print(f"{len(elides):,} eliding stems → {args.elide}", file=sys.stderr)

    rows = sorted(((n, c, s, r) for (c, s, r), n in counts.items()
                   if n >= args.min_count),
                  key=lambda row: (-row[0], row[1], row[2], row[3]))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as fh:
        fh.write("# class\tstrip\tresidue\tcount"
                 " — generated by tools/mine_residues.py\n")
        for n, cls, strip, residue in rows:
            fh.write(f"{cls}\t{strip or '0'}\t{residue}\t{n}\n")

    kept = sum(row[0] for row in rows)
    print(f"{len(rows):,} (class, residue) pairs over {kept:,} forms "
          f"→ {args.output}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
