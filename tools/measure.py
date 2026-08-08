"""Measure what fraction of real Kazakh word forms a dictionary accepts.

Recall on its own says a dictionary is bad without saying why, and the two
causes want completely different work: a rejected form whose stem is already a
headword is an affix problem, one whose stem is absent is a wordlist problem.
So every rejection is stemmed with `kazsearch` and charged to one side or the
other.

    python tools/measure.py baseline/kk_KZ
    python tools/measure.py dict/kk_KZ --against baseline/kk_KZ
    python tools/measure.py dict/kk_KZ --misses out/   # dump rejections

Needs `hunspell` on PATH and a checkout of kazsearch-py (--kazsearch, or
KAZSEARCH_SRC, default ../kazsearch-py).
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_KAZSEARCH = Path(os.environ.get("KAZSEARCH_SRC", ROOT.parent / "kazsearch-py"))

# The corpus ships with kazsearch-py, not here: it is third-party text of
# uncertain provenance, and vendoring it would attach that question to the
# dictionary's licence.
DEFAULT_CORPUS = "tests/golden_corpus.tsv"
CORPUS_CACHE = ROOT / "tests/corpus_cyr.txt"

CYRILLIC_WORD = re.compile(r"^[Ѐ-ӿ]+$")

UNCAPPED = 1024


def extract_corpus(source: Path) -> list[str]:
    """Cyrillic word forms from the first column of a golden TSV.

    The other column is a Latin transliteration, and the file also carries
    Latin-script and numeric tokens that a Cyrillic dictionary is not being
    asked about.
    """
    words = []
    for line in source.read_text(encoding="utf-8").splitlines():
        w = line.split("\t")[0].strip()
        if CYRILLIC_WORD.match(w):
            words.append(w)
    return words


def load_corpus(args: argparse.Namespace) -> list[str]:
    if args.corpus:
        source = args.corpus
    else:
        source = args.kazsearch / DEFAULT_CORPUS
        if CORPUS_CACHE.exists() and CORPUS_CACHE.stat().st_mtime >= source.stat().st_mtime:
            return CORPUS_CACHE.read_text(encoding="utf-8").split()
    if not source.exists():
        sys.exit(f"no corpus at {source} — pass --corpus or --kazsearch")
    words = extract_corpus(source)
    CORPUS_CACHE.parent.mkdir(parents=True, exist_ok=True)
    CORPUS_CACHE.write_text("\n".join(words) + "\n", encoding="utf-8")
    return words


def headwords(dic: Path) -> set[str]:
    """The lemmas a .dic declares, without their affix flags.

    The first line is the entry count, and a `/` separates the word from its
    flags — except that a leading `/` would be an escaped one, which no Kazakh
    entry has.
    """
    out = set()
    text = dic.read_text(encoding="utf-8-sig")
    for line in text.splitlines()[1:]:
        line = line.strip()
        if line:
            out.add(line.split("/")[0].split("\t")[0].lower())
    return out


def spellcheck(base: Path, words: list[str]) -> list[str]:
    """Rejections, in corpus order.

    hunspell is handed the pair through a temp directory because it insists on
    finding `<base>.aff` and `<base>.dic` side by side, and because a UTF-8 BOM
    on the .aff makes it misread the first directive — the shipped 2009 files
    have one and are kept byte-for-byte as published.
    """
    with tempfile.TemporaryDirectory() as tmp:
        stage = Path(tmp) / base.name
        for ext in (".aff", ".dic"):
            data = (base.parent / (base.name + ext)).read_bytes()
            stage.with_suffix(ext).write_bytes(data.removeprefix(b"\xef\xbb\xbf"))
        proc = subprocess.run(
            ["hunspell", "-d", str(stage), "-l"],
            input="\n".join(words), capture_output=True, text=True,
        )
    if proc.returncode != 0:
        sys.exit(f"hunspell failed: {proc.stderr.strip()}")
    return proc.stdout.split()


def classify(misses: list[str], heads: set[str], ladder) -> tuple[list[str], list[str]]:
    """Split rejections into affix gap and wordlist gap."""
    morph, vocab = [], []
    for w in misses:
        target = morph if any(r in heads for r in ladder(w, max_rungs=UNCAPPED)) else vocab
        target.append(w)
    return morph, vocab


def report(name: str, total: int, morph: list[str], vocab: list[str]) -> float:
    misses = len(morph) + len(vocab)
    recall = (1 - misses / total) * 100
    print(f"{name}")
    print(f"  forms tested   {total:>8,}")
    print(f"  recall         {recall:>8.1f}%")
    print(f"  rejected       {misses:>8,}")
    print(f"    affix gap    {len(morph):>8,}   {len(morph) / max(misses, 1) * 100:4.1f}%"
          "   stem is a headword, the rules cannot reach the form")
    print(f"    wordlist gap {len(vocab):>8,}   {len(vocab) / max(misses, 1) * 100:4.1f}%"
          "   no analysis of the form is a headword")
    return recall


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dictionary", type=Path,
                    help="path without extension, e.g. baseline/kk_KZ")
    ap.add_argument("--against", type=Path, help="also measure this and show the delta")
    ap.add_argument("--corpus", type=Path, help="word list or golden TSV to test with")
    ap.add_argument("--kazsearch", type=Path, default=DEFAULT_KAZSEARCH)
    ap.add_argument("--misses", type=Path, help="directory to dump rejections into")
    args = ap.parse_args()

    if not shutil.which("hunspell"):
        sys.exit("hunspell is not on PATH")
    sys.path.insert(0, str(args.kazsearch / "src"))
    try:
        from kazsearch.ladder import ladder
    except ImportError:
        sys.exit(f"no kazsearch under {args.kazsearch} — pass --kazsearch")

    words = load_corpus(args)

    results = {}
    for base in filter(None, [args.dictionary, args.against]):
        heads = headwords(base.parent / (base.name + ".dic"))
        morph, vocab = classify(spellcheck(base, words), heads, ladder)
        results[base] = report(str(base), len(words), morph, vocab)
        if args.misses:
            args.misses.mkdir(parents=True, exist_ok=True)
            for kind, ws in (("affix", morph), ("wordlist", vocab)):
                (args.misses / f"{base.name}.{kind}.txt").write_text(
                    "\n".join(ws) + "\n", encoding="utf-8")
        print()

    if args.against:
        delta = results[args.dictionary] - results[args.against]
        print(f"delta {delta:+.1f} points against {args.against}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
