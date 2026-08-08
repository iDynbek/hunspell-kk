"""Work out which headwords the affix file has made unnecessary.

The 2009 wordlist enters inflected forms as headwords in their own right —
`абай`, `абайдан` and `абайдың` are three of its 54,063 entries. That padding
was how a one-suffix affix file coped. It is not free now: an inflected form
entered as a stem gets a class flag of its own, and suffixes then stack on top
of an already-inflected word, which is where `*аккумуляторыдың` comes from.

Deciding what is safe to drop takes two passes, both empirical.

**Redundant.** Build the dictionary without every candidate at once and keep
back whatever Hunspell then rejects. Removing them together is the conservative
direction — a word only goes if it survives the removal of everything else that
might have explained it — and it keeps derivations like `абайсыздық`, which the
ladder cannot tell from an inflection but the rules cannot produce.

**Load-bearing.** A regenerable headword can still be the stem of something
longer: dropping all 21,494 costs 20,170 corpus forms, because the affix file
only knows the suffix strings that were mined against the stems it had. Those
5,451 entries come back.

    python tools/prune.py -o data/prune.txt

The result is committed so that building the dictionary needs only this
repository; recomputing it needs a corpus, kazsearch-py and hunspell.
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

from gen_dic import entry, read_lexicon  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_KAZSEARCH = Path(os.environ.get("KAZSEARCH_SRC", ROOT.parent / "kazsearch-py"))

UNCAPPED = 1024


def spell(aff: Path, words: dict[str, str], probe: list[str]) -> set[str]:
    """Which of `probe` a dictionary of exactly `words` rejects."""
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp) / "trial"
        base.with_suffix(".aff").write_bytes(aff.read_bytes())
        base.with_suffix(".dic").write_text(
            f"{len(words)}\n"
            + "\n".join(sorted(entry(w, t) for w, t in words.items())) + "\n",
            encoding="utf-8")
        proc = subprocess.run(["hunspell", "-d", str(base), "-l"],
                              input="\n".join(probe), capture_output=True, text=True)
    if proc.returncode != 0:
        sys.exit(f"hunspell failed: {proc.stderr.strip()}")
    return set(proc.stdout.split())


def read_sources(path: Path) -> dict[str, tuple[str, str]]:
    """word → (its tracks, the sources that list it)."""
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line and not line.startswith("#"):
            word, tracks, sources = line.split("\t")
            out[word] = (tracks, sources)
    return out


def rank(word: str, sources: dict[str, tuple[str, str]]) -> tuple[int, int, int]:
    """How much a headword looks like a real lexeme rather than 2009 padding.

    An entry only the 2009 wordlist has, and that nothing gives a part of
    speech, is the signature of an inflected form entered as a headword to work
    around a one-suffix affix file. `адамдық` is a noun in all three sources;
    `адамды` is untagged and in the baseline alone. When either would explain a
    form, the first is the one that should stay.
    """
    tracks, origin = sources.get(word, ("-", ""))
    vouching = set(origin.split(",")) - {"baseline"}
    return (tracks != "-", len(vouching), len(word))


def admissible(word: str, covered: int, sources: dict[str, tuple[str, str]],
               min_cover: int) -> bool:
    """Whether a pruned headword has earned its way back.

    An entry no source gives a part of speech and only the 2009 wordlist has is
    the signature of an inflected form entered as a headword. One of those
    should not return on the strength of a couple of forms, because the corpus
    has typos in it and they are exactly what such an entry explains: `адамды`
    was kept alive by `адамдын`, a misspelling of `адамдың`, and in exchange it
    licensed `*адамдың` for every noun in its class.

    Anything a real source vouches for comes back on a single form.
    """
    tracks, origin = sources.get(word, ("-", ""))
    vouched = tracks != "-" or set(origin.split(",")) - {"baseline"}
    return bool(vouched) or covered >= min_cover


def restore(lost: set[str], redundant: set[str],
            sources: dict[str, tuple[str, str]], ladder, min_cover: int) -> set[str]:
    """The smallest set of pruned headwords that explains the lost forms.

    The exhaustive answer — every pruned rung of every lost form — is what let
    `адамды` back in: `адамдығымды` has both it and `адамдық` on its ladder, so
    both returned, and the one that should not have licensed `*адамдың`.

    Greedy set cover instead, taking whichever candidate covers the most forms
    still uncovered and breaking ties on `rank`.
    """
    covers = collections.defaultdict(set)
    for form in lost:
        for rung in ladder(form.lower(), max_rungs=UNCAPPED):
            if rung in redundant:
                covers[rung].add(form)
    if not covers:
        return set()

    uncovered = {form for forms in covers.values() for form in forms}
    chosen = set()
    while uncovered:
        best = max(covers, key=lambda w: (len(covers[w] & uncovered), rank(w, sources)))
        gained = covers[best] & uncovered
        if not gained:
            break
        if admissible(best, len(gained), sources, min_cover):
            chosen.add(best)
            uncovered -= gained
        covers.pop(best)
    return chosen


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-o", "--output", type=Path, default=ROOT / "data/prune.txt")
    ap.add_argument("--lexicon", type=Path, default=ROOT / "data/lexicon.tsv")
    ap.add_argument("--aff", type=Path, default=ROOT / "dict/kk_KZ.aff")
    ap.add_argument("--corpus", type=Path, default=ROOT / "tests/corpus_cyr.txt")
    ap.add_argument("--kazsearch", type=Path, default=DEFAULT_KAZSEARCH)
    ap.add_argument("--min-cover", type=int, default=3,
                    help="forms an untagged baseline-only entry must explain "
                         "before it is restored")
    args = ap.parse_args()

    if not args.corpus.exists():
        sys.exit(f"no corpus at {args.corpus} — run `make baseline` first")
    sys.path.insert(0, str(args.kazsearch / "src"))
    try:
        from kazsearch.ladder import ladder
    except ImportError:
        sys.exit(f"no kazsearch under {args.kazsearch} — pass --kazsearch")

    words = read_lexicon(args.lexicon)
    sources = read_sources(args.lexicon)

    # A word may only be pruned if it reduces to a shorter headword by removing
    # *inflection* — case, plural, possessive. A word that is a shorter headword
    # plus a derivation is a distinct lexeme with its own paradigm: `бөлімше`
    # (subdivision) is `бөлім` plus the derivational `-ше`, and pruning it on
    # the grounds that `бөлім+ше` regenerates the bare form loses `бөлімшеге`,
    # because no mined chain carries `-ше` followed by every case. That broke a
    # long tail of common legal-register words.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from mine_harmony import inflectional
    endings = inflectional(args.kazsearch)

    def inflection_only(word: str, base: str) -> bool:
        residue = word[len(base):]
        while residue:
            for end in sorted(endings, key=len, reverse=True):
                if residue.startswith(end):
                    residue = residue[len(end):]
                    break
            else:
                return False
        return True

    candidates = {w for w in words
                  if any(rung in words and rung != w and w.startswith(rung)
                         and inflection_only(w, rung)
                         for rung in ladder(w, max_rungs=UNCAPPED))}

    keep = {w: t for w, t in words.items() if w not in candidates}
    redundant = candidates - spell(args.aff, keep, sorted(candidates))
    print(f"{len(candidates):,} candidates, {len(redundant):,} regenerable",
          file=sys.stderr)

    corpus = args.corpus.read_text(encoding="utf-8").split()
    baseline_rejects = spell(args.aff, words, corpus)
    lost = (spell(args.aff, {w: t for w, t in words.items() if w not in redundant},
                  corpus)
            - baseline_rejects)
    print(f"{len(lost):,} forms would be lost", file=sys.stderr)

    load_bearing = restore(lost, redundant, sources, ladder, args.min_cover)
    print(f"{len(load_bearing):,} entries restored", file=sys.stderr)

    # Restoring a set chosen by ranking is a guess until Hunspell agrees, so
    # check, and fall back to the exhaustive answer for anything still missing.
    kept = {w: t for w, t in words.items()
            if w not in redundant or w in load_bearing}
    still = spell(args.aff, kept, sorted(lost)) - baseline_rejects
    if still:
        extra = restore(still, redundant, sources, ladder, args.min_cover) - load_bearing
        load_bearing |= extra
        print(f"{len(still):,} forms still missing, {len(extra):,} more restored",
              file=sys.stderr)

    drop = sorted(redundant - load_bearing)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        "# headwords the affix file regenerates, generated by tools/prune.py\n"
        + "\n".join(drop) + "\n", encoding="utf-8")
    print(f"{len(drop):,} headwords → {args.output}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
